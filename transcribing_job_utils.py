import boto3
import csv
import json
import logging
import pandas as pd
import re
import os
import time
from botocore.exceptions import ClientError
from typing import List, Tuple, Optional


def check_assertions(input_folder: str, output_folder: str, version: str) -> None:
    """
    Check assertions for input_folder, output_folder, version, and format.
    Args:
        input_folder: The input folder path.
        output_folder: The output folder path.
        version: The version string.
    Raises:
        AssertionError: If any of the assertions fail.
    """
    assert (
        len(input_folder.split("/")) == 3
    ), "The input folder needs to look like data/audio/"
    assert re.match(
        r"^[a-zA-Z]+/$", output_folder
    ), "The output folder needs to look like 'transcriptions/'"
    assert (
        len(version) == 1 and version.isalpha()
    ), "The version needs to be alphabetical and have one letter"


def get_access_credentials(file_path: str) -> Tuple[str, str]:
    """
    Gets access credentials from .csv downloaded from AWS.
    Args:
        file_path: The path to the CSV file.
    Returns:
        Tuple[str, str]: Access key and secret key.
    """
    with open(file_path, "r") as f:
        rows = []
        for row in csv.reader(f):
            rows.append(row)
    access_key = rows[1][0]
    secret_key = rows[1][1]
    return access_key, secret_key


def is_transcribable_file(
    file_path: str,
    supported_extensions: List[str] = [
        ".mp3",
        ".wav",
        ".flac",
        ".ogg",
        ".m4a",
        ".mp4",
        ".mov",
    ],
) -> bool:
    """
    Checks if the file with the given path can be transcribed by AWS Transcribe.
    Args:
        file_path: The path to the file.
        supported_extensions: List of supported file extensions.
    Returns:
        bool: True if the file is transcribable, False otherwise.
    """

    transcribable_file = True
    _, file_extension = os.path.splitext(file_path)

    if (
        not os.path.exists(file_path)
        or not os.path.isfile(file_path)
        or file_extension.lower() not in supported_extensions
    ):
        transcribable_file = False

    return transcribable_file


def bucket_names(s3_client) -> List[str]:
    """
    Displays a list of bucket names.
    Args:
        s3_client: The Boto3 S3 client.
    Returns:
        List[str]: List of bucket names.
    """
    response = s3_client.list_buckets()
    bucket_names = []
    for bucket in response["Buckets"]:
        bucket_names.append(bucket["Name"])
    return bucket_names


def create_bucket(s3_client, bucket_name: str, region: str) -> None:
    """
    Create bucket if it doesn't exist.
    Args:
        s3_client: The Boto3 S3 client.
        bucket_name: The name of the bucket.
        region: The region of the bucket.
    """
    if not bucket_name in bucket_names(s3_client):
        try:
            location = {"LocationConstraint": region}
            s3_client.create_bucket(
                Bucket=bucket_name, CreateBucketConfiguration=location
            )
        except ClientError as e:
            logging.error(e)
            return False
        print(f"Bucket {bucket_name} created.")
    else:
        print(f"Bucket {bucket_name} already exists.")


def folder_upload(s3_client, bucket_name: str, input_folder: str) -> None:
    """
    Creates cloud folder and uploads transcribable files from
    a local folder to a folder in the given bucket with the same name.
    Args:
        s3_client: The Boto3 S3 client.
        bucket_name: The name of the bucket.
        input_folder: The local input folder path.
    """

    input_cloud = input_folder.split("/")[-2] + "/"
    s3_client.put_object(Bucket=bucket_name, Key=input_cloud)

    for root, dirs, files in os.walk(input_folder):
        for file in files:
            file_path = os.path.join(root, file)
            if is_transcribable_file(file_path):
                try:
                    s3_client.upload_file(file_path, bucket_name, input_cloud + file)
                except ClientError as e:
                    logging.error(e)
                    return False
    print(f"Folder {input_folder} uploaded.")


def create_vocabulary(
    vocabulary_name: str,
    language_code: str,
    transcribe_client,
    phrases: List[str] = None,
    table_uri: str = None,
) -> dict:
    """
    Creates a custom vocabulary that can be used to improve the accuracy of transcription jobs.
    Args:
        vocabulary_name: The name of the vocabulary.
        language_code: The language code.
        transcribe_client: The Boto3 Transcribe client.
        phrases: List of phrases to include in the vocabulary.
        table_uri: URI of the table containing phrases.
    Returns:
        dict: Response from the create_vocabulary API call.
    """
    try:
        vocab_args = {"VocabularyName": vocabulary_name, "LanguageCode": language_code}
        if phrases is not None:
            vocab_args["Phrases"] = phrases
        elif table_uri is not None:
            vocab_args["VocabularyFileUri"] = table_uri
        response = transcribe_client.create_vocabulary(**vocab_args)
        print("Created custom vocabulary")
    except ClientError as e:
        logging.error(e)
    

def get_vocabulary(vocabulary_name: str, transcribe_client) -> dict:
    """
    Gets information about a custom vocabulary.
    Args:
        vocabulary_name: The name of the vocabulary to retrieve.
        transcribe_client: The Boto3 Transcribe client.
    Returns:
        dict: Information about the vocabulary.
    """
    
    try:
        response = transcribe_client.get_vocabulary(VocabularyName=vocabulary_name)
        logging.info("Got vocabulary %s.", response["VocabularyName"])
    except ClientError:
        logging.exception("Couldn't get vocabulary %s.", vocabulary_name)
        raise
    else:
        while True:
            response = transcribe_client.get_vocabulary(VocabularyName=vocabulary_name)
            job_status = response["VocabularyState"]
            if job_status == "READY":
                print('Vocabulary ready.')
                break
            elif job_status == 'FAILED':
                raise Exception("Vocabulary processing failed.")
            else:
                time.sleep(10)
        

def transcribe_file(
    job_name: str,
    file_uri: str,
    transcribe_client,
    bucket_name: str,
    output_folder: str,
    lang_code: str,
    format: str,
    vocabulary_name: Optional[str] = None,
) -> None:
    """
    Transcribes the audio to the specified folder in the bucket.
    Args:
        job_name: The name of the transcription job.
        file_uri: The URI of the audio file.
        transcribe_client: The Boto3 Transcribe client.
        bucket_name: The name of the S3 bucket.
        output_folder: The folder in the bucket for the output.
        lang_code: The language code.
        format: The audio file format.
        vocabulary_name: The name of the custom vocabulary (if any).
    """
    try:
        job_args = {
            "TranscriptionJobName": job_name,
            "Media": {"MediaFileUri": file_uri},
            "MediaFormat": format,
            "LanguageCode": lang_code,
            "OutputBucketName": bucket_name,
            "OutputKey": output_folder,
        }
        if vocabulary_name is not None:
            job_args["Settings"] = {"VocabularyName": vocabulary_name}

        transcribe_client.start_transcription_job(**job_args)
    except ClientError as e:
        logging.error(e)
    else:
        while True:
            job = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
            job_status = job["TranscriptionJob"]["TranscriptionJobStatus"]
            if job_status in ["COMPLETED", "FAILED"]:
                break
            else:
                time.sleep(10)


def transcribe_folder(
    s3_client,
    transcribe_client,
    bucket_name: str,
    input_folder: str,
    output_folder: str,
    lang_code: str,
    format: str,
    version: str,
    vocabulary_name: Optional[str] = None,
) -> int:
    """
    Transcribes all audio files in a folder in the S3 bucket.
    Args:
        s3_client: The Boto3 S3 client.
        transcribe_client: The Boto3 Transcribe client.
        bucket_name: The name of the S3 bucket.
        input_folder: The folder in the bucket with audio files.
        output_folder: The folder in the bucket for the output transcriptions.
        lang_code: The language code.
        format: The audio file format.
        version: The version string.
        vocabulary_name: The name of the custom vocabulary (if any).
    Returns:
        int: The number of jobs processed.
    """
    input_cloud = input_folder.split("/")[-2] + "/"
    response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=input_cloud)
    job_count = 0
    for r in response["Contents"][1:]:
        try:
            file_uri = f"https://{bucket_name}.s3.amazonaws.com/{r['Key']}"
            job_name = version + re.search(r"\/(.*?)\.", r["Key"]).group(1)
            transcribe_file(
                job_name,
                file_uri,
                transcribe_client,
                bucket_name,
                output_folder,
                lang_code,
                format,
                vocabulary_name,
            )
            job_count += 1
        except ClientError as e:
            logging.error(e)
            print(f"Error for file {r}")
        continue
    print("Folder transcribed.")
    return job_count


def download_folder(
    s3_client, bucket_name: str, output_folder: str, job_count: int
) -> None:
    """
    Downloads transcripts from S3 bucket.
    Args:
        s3_client: The Boto3 S3 client.
        bucket_name: The name of the S3 bucket.
        output_folder: The folder in the bucket containing transcripts.
        job_count: The number of jobs to download.
    """
    local_directory = f"./{output_folder}"
    os.makedirs(local_directory, exist_ok=True)

    while True:
        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=output_folder)
        if len(response["Contents"][1:]) == job_count:
            break
        else:
            time.sleep(10)

    for r in response["Contents"][1:]:
        try:
            object_key = r["Key"]
            local_file_path = os.path.join(local_directory, object_key.split("/")[1])
            file = s3_client.download_file(bucket_name, object_key, local_file_path)
        except ClientError as e:
            logging.error(e)

    print("Folder downloaded.")


def get_transcript(path: str) -> str:
    """
    Retrieves transcript data from a JSON file.
    Args:
        path (str): The path to the JSON file.
    Returns:
        str: The transcript data.
    """
    with open(path, "r") as f:
        output = json.load(f)
    transcript_data = output["results"]["transcripts"][0]["transcript"]
    return transcript_data


def transcripts_to_csv(output_folder: str, csv_path: str) -> None:
    """
    Converts transcripts from JSON files to a CSV file.
    Args:
        output_folder: The folder containing JSON files.
        csv_path: The path to the CSV file.
    """
    files = [
        file
        for file in os.listdir(output_folder)
        if os.path.isfile(os.path.join(output_folder, file))
    ]
    transcripts = []
    ids = []
    for file in files:
        id = file.split(".")[0][1:]
        path = os.path.join(output_folder, file)
        transcript = get_transcript(path)
        transcripts.append(transcript)
        ids.append(id)

    df = pd.DataFrame({"Id": ids, "Amazon Transcript": transcripts})
    df.to_csv(csv_path, index=False)
    print(df.head())


def delete_all_transcription_jobs(transcribe_client) -> None:
    """
    Deletes all transcription jobs.
    Args:
        transcribe_client: The Boto3 Transcribe client.
    """
    while True:
        try:
            response = transcribe_client.list_transcription_jobs()

            if "TranscriptionJobSummaries" in response:
                transcription_jobs = response["TranscriptionJobSummaries"]

                for job in transcription_jobs:
                    job_name = job["TranscriptionJobName"]
                    transcribe_client.delete_transcription_job(
                        TranscriptionJobName=job_name
                    )
            else:
                break

        except Exception as e:
            logging.error(e)
            print(f"An error occurred: {e}")


def delete_s3_folder(s3, bucket_name: str, output_folder: str) -> None:
    """
    Deletes all objects in an S3 bucket folder.
    Parameters:
        s3: The Boto3 S3 client.
        bucket_name: The name of the S3 bucket.
        output_folder: The folder to delete.
    """
    objects_to_delete = []
    response = s3.list_objects_v2(Bucket=bucket_name, Prefix=output_folder)

    for obj in response.get("Contents", []):
        objects_to_delete.append({"Key": obj["Key"]})

    if objects_to_delete:
        s3.delete_objects(Bucket=bucket_name, Delete={"Objects": objects_to_delete})
    s3.delete_object(Bucket=bucket_name, Key=output_folder)
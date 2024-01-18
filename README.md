# Evaluation of Amazon Transcribe Performance 

## Project Structure:

- **Data Folder:**
  - Contains CSV files:
    - Extracted data from [Airtable](https://airtable.com/appvWk23jLudQRWKu/shr1BF9rWJsTE70zZ/tblwP2dpg02WHUA4B/viw79dPwj3BlbsKSi?blocks=hide)
    - Transcriptions without improvement
    - Transcriptions with improvement

- **Main Files:**
  - [AmazonTranscribeEvaluation.ipynb](AmazonTranscribeEvaluation.ipynb) - The main notebook.

- **Utility Files:**
  - [youtube_download.py](youtube_download.py) - Script to download audios within a given timestamp.
  - [transcribing_job_utils.py](transcribing_job_utils.py) - Utilities for transcribing jobs of a folder.
  - [utilities.py](utilities.py) - Helper functions to run the main notebook.

- **Vocabulary Files:**
  - [custom_vocab.txt](custom_vocab.txt) - File to create a vocabulary with the phrases parameter.
  - [input_vocab.txt](input_vocab.txt) - File with table-like vocabulary to create a vocabulary with the table_uri parameter.

- [transcribing_test.ipynb](transcribing_test.ipynb): Presents transcribing job for one file in a folder.

## Running the Notebook:

1. Clone the repository.
2. Create a virtual environment and install dependencies using `requirements.txt`.
3. Download AWS access key for a client with permissions for the use of S3 and Amazon Transcribe.

## Key Insights from the Analysis:

**Metrics and Data:**
- The incorporation of metrics and the ground truth are not optimal. The ground truth also comes with errors. The interpretation of metrics for speech recognition, such as WER and CER, could be broad.

**Amazon Transcribe:**
- Doesn't have hyphenated words in its vocabulary.
- Transcribes numbers in a specific way.
- Web links, names, and acronyms are particularly challenging; they should be delivered in a table as custom vocabulary.
- Formal language was much easier to transcribe.
- Noise, the number of speakers, and audio quality had an impact on output.
- In general, the average WER reached 14 per 100 misspecified words.
- Creating vocabulary as a list of phrases was ineffective, especially for names and websites; the metric improvement was marginal.



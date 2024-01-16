import os
from pytube import YouTube
from typing import List
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip


def download_yt_audio(
    urls: List[str],
    file_names: List[str],
    starts: List[int],
    ends: List[int],
    folder: str = "audios",
) -> None:
    """Downloads youtube audio if available, trims to specific timestamp and saves
    in folder.
    Args:
        urls: List of YouTube video URLs.
        file_names: List of desired file names for the downloaded and trimmed audio.
        starts: List of start timestamps (in seconds) for trimming.
        ends: List of end timestamps (in seconds) for trimming.
        folder: Folder to save the audio files. Defaults to 'audios'.
    Returns:
        None
    """
    os.makedirs(folder, exist_ok=True)

    for url, file_name, start, end in zip(urls, file_names, starts, ends):
        try:
            yt = YouTube(url)
            audio = yt.streams.filter(only_audio=True, file_extension="mp4").first()
            audio.download(folder)
            default_path = os.path.join(folder, audio.default_filename)
            target_name = os.path.join(folder, file_name)
            ffmpeg_extract_subclip(default_path, start, end, targetname=target_name)
            os.remove(default_path)
        except:
            pass

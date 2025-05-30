# utils.py
import os
# from urllib.parse import urlparse # Not strictly needed by is_youtube_url as implemented

def is_youtube_url(path_string):
    if not path_string:
        return False
    path_string_lower = path_string.lower()
    return path_string_lower.startswith(("https://www.youtube.com/", "https://youtu.be/",
                                         "http://www.youtube.com/", "http://youtu.be/"))

def get_playable_path_info(perf_data_dict):
    """
    Determines the best playable path from a performance data dictionary.
    Returns: (path_or_url_string, is_youtube_url_bool)
    Priority: file_path1, file_path2, file_url.
    """
    path1 = perf_data_dict.get("file_path1")
    # Temporarily assume path1 exists if the field is not empty
    if path1: # OLD: if path1 and os.path.exists(path1):
        return path1, False

    path2 = perf_data_dict.get("file_path2")
    # Temporarily assume path2 exists if the field is not empty  
    if path2: # OLD: if path2 and os.path.exists(path2):
        return path2, False

    file_url = perf_data_dict.get("file_url")
    if file_url:
        is_yt = is_youtube_url(file_url)
        return file_url, is_yt
    return None, False
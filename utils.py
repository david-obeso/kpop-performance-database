# utils.py
import os
import re
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

def extract_date_from_filepath(filepath):
    """
    Extracts a date in yymmdd format from the first 6 characters of a filepath.
    
    Args:
        filepath (str): A Linux filepath
        
    Returns:
        str: The date in yymmdd format if the first 6 characters are numerical and form a valid date,
             None otherwise.
    """
    # Extract filename from path
    filename = os.path.basename(filepath)
    
    # Check if the first 6 characters are digits
    if len(filename) >= 6 and filename[:6].isdigit():
        yymmdd = filename[:6]
        yy = int(yymmdd[:2])
        mm = int(yymmdd[2:4])
        dd = int(yymmdd[4:6])
        
        # Basic date validation
        if (0 <= yy <= 99) and (1 <= mm <= 12) and (1 <= dd <= 31):
            # Additional validation for days in month
            if mm in [4, 6, 9, 11] and dd > 30:
                return None
            elif mm == 2:
                # Simple leap year check (not perfect but sufficient for our use case)
                leap_year = (yy % 4 == 0)
                if (leap_year and dd > 29) or (not leap_year and dd > 28):
                    return None
            return yymmdd
    
    return None

def find_string_in_filename(filepath, search_strings):
    """
    Check if any of the specified strings are present in the filename portion of a filepath.
    
    Args:
        filepath (str): A filepath
        search_strings (list or str): A string or list of strings to search for in the filename
        
    Returns:
        list: A list of strings from search_strings that were found in the filename,
              or an empty list if none were found
    """
    # Extract filename from path
    filename = os.path.basename(filepath)
    
    # Handle both single string and list inputs
    if isinstance(search_strings, str):
        search_strings = [search_strings]
    
    # Check which strings are in the filename
    found_matches = []
    for search_string in search_strings:
        if search_string in filename:
            found_matches.append(search_string)
    
    return found_matches
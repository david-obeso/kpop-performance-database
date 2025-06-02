# utils.py
# Utility functions for the K-pop performance database application
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
    Enhanced to better handle multi-word artist names by using different matching strategies.
    
    Args:
        filepath (str): A filepath
        search_strings (list or str): A string or list of strings to search for in the filename
        
    Returns:
        list: A list of strings from search_strings that were found in the filename,
              in order of confidence (most confident first), or an empty list if none were found
    """
    # Extract filename from path
    filename = os.path.basename(filepath)
    
    # Handle both single string and list inputs
    if isinstance(search_strings, str):
        search_strings = [search_strings]
    
    # Prepare normalized versions of the filename
    # 1. Convert to lowercase for case-insensitive matching
    filename_lower = filename.lower()
    # 2. Replace common delimiters with spaces
    normalized_filename = re.sub(r'[_\-.]', ' ', filename_lower)
    # 3. Create a version with no spaces
    nospace_filename = re.sub(r'\s+', '', normalized_filename)
    
    # Different match levels with confidence scores
    exact_matches = []  # Highest confidence
    normalized_matches = []  # Medium confidence
    nospace_matches = []  # Lower confidence
    
    for search_string in search_strings:
        search_lower = search_string.lower()
        search_normalized = re.sub(r'[_\-.]', ' ', search_lower)
        search_nospace = re.sub(r'\s+', '', search_normalized)
        
        # Check for exact match in original filename (highest confidence)
        if search_string in filename or search_lower in filename_lower:
            exact_matches.append(search_string)
        
        # Check for match in normalized filename (spaces, underscores, hyphens normalized)
        elif search_normalized in normalized_filename:
            normalized_matches.append(search_string)
            
        # Check for match with no spaces (for cases like RedVelvet vs Red Velvet)
        elif search_nospace in nospace_filename:
            nospace_matches.append(search_string)
            
        # For multi-word searches, check if all words appear in the filename
        elif ' ' in search_normalized:
            words = search_normalized.split()
            if all(word in normalized_filename for word in words):
                normalized_matches.append(search_string)

    # Return matches in order of confidence
    return exact_matches + normalized_matches + nospace_matches

def find_artist_in_filename(filepath, artist_list, detailed=False):
    """
    Specialized function to find artist names in filenames with high accuracy.
    
    Args:
        filepath (str): A filepath
        artist_list (list): A list of artist dictionaries with 'id' and 'name' keys
        detailed (bool): Whether to return detailed matching information (default: False)
        
    Returns:
        dict or tuple: The artist dictionary with the highest confidence match or None if no match.
                      If detailed=True, returns (artist_dict, confidence_score, match_type)
    """
    if not filepath or not artist_list:
        return None
        
    # Get the filename
    filename = os.path.basename(filepath)
    filename_lower = filename.lower()
    
    # Create a scoring system for matches
    matches = []
    
    for artist in artist_list:
        artist_name = artist['name']
        artist_lower = artist_name.lower()
        
        score = 0
        match_type = None
        
        # Check for exact match
        if artist_name in filename or artist_lower in filename_lower:
            score = 100
            match_type = "exact"
        
        # Normalize both strings for comparison
        artist_norm = re.sub(r'[_\-.]', ' ', artist_lower)
        filename_norm = re.sub(r'[_\-.]', ' ', filename_lower)
        
        # Check for normalized match
        if score == 0 and artist_norm in filename_norm:
            score = 80
            match_type = "normalized"
        
        # Check for no-space match (this handles cases like "GirlsGeneration" vs "Girls Generation")
        if score == 0:
            artist_nospace = re.sub(r'\s+', '', artist_norm)
            filename_nospace = re.sub(r'\s+', '', filename_norm)
            
            # Special pattern check for multi-word artists with no spaces
            if ' ' in artist_norm and artist_nospace in filename_nospace:
                # Prioritize multi-word artists with higher scores
                word_count = len(artist_norm.split())
                # Base score plus bonuses for length and word count
                score = 70 + min(len(artist_nospace) // 2, 15) + (word_count * 5)
                match_type = "nospace-multiword"
            elif artist_nospace in filename_nospace:
                # Regular no-space match for single-word artists
                score = 60 + min(len(artist_nospace) // 2, 15)
                match_type = "nospace"
        
        # For multi-word artists, check if all words are in the filename
        if score == 0 and ' ' in artist_norm:
            words = artist_norm.split()
            
            # Check if all words from the artist name are in the filename
            all_words_match = all(word in filename_norm for word in words)
            
            if all_words_match:
                # The longer the artist name (more words), the higher the confidence
                score = 40 + min(len(words) * 5, 30)  # Cap at 70
                
                match_type = "words"
                
                # Bonus if the words appear close to each other
                word_positions = []
                for word in words:
                    if word in filename_norm:
                        word_positions.append(filename_norm.find(word))
                
                if word_positions:
                    max_gap = max(word_positions) - min(word_positions)
                    # Smaller gaps = higher confidence
                    if max_gap < len(' '.join(words)) * 2:
                        score += 10
                        
                # Add bonus for longer, more specific artist names to avoid short names matching everywhere
                if len(artist_lower) > 3:  # More than 3 characters
                    score += min(len(artist_lower), 10)  # Up to 10 bonus points for long names
                    
        # Additional check for very short artist names (like "IVE") to avoid false positives
        if score > 0:
            if len(artist_lower) <= 3:  # Very short name (like "IVE")
                # For very short names, we should be more strict to avoid false matches
                if match_type not in ["exact", "normalized"]:
                    # Penalize short names that aren't exact matches
                    score -= 30
                    
            # Additional check for substring issues (e.g., "IVE" in "annIVErsary")
            # Apply this check to any short artist name or known problematic ones
            if len(artist_lower) <= 5 or artist_lower in ["ive", "the", "in", "on", "at", "to", "and"]:
                # Check if the artist name might be part of another word
                artist_pos = filename_lower.find(artist_lower)
                if artist_pos > 0 and artist_pos + len(artist_lower) < len(filename_lower):
                    # Check characters before and after the match
                    char_before = filename_lower[artist_pos - 1]
                    char_after = filename_lower[artist_pos + len(artist_lower)]
                    if char_before.isalpha() or char_after.isalpha():
                        # It's likely part of another word, so heavily penalize
                        # The penalty is proportional to how short the name is
                        penalty = 70 - (len(artist_lower) * 10)  # Shorter names get bigger penalties
                        score -= max(30, min(penalty, 50))  # Between 30-50 depending on length
                        
        # If we found a match, add it to our list
        if score > 0:
            matches.append({
                'artist': artist,
                'score': score,
                'match_type': match_type
            })
    
    # Sort matches by score (highest first)
    matches.sort(key=lambda x: x['score'], reverse=True)
    
    # Special case: If we have multiple matches and they're very close in score,
    # prefer the longer artist name as it's likely more specific
    if len(matches) > 1:
        top_score = matches[0]['score']
        close_matches = [m for m in matches if m['score'] >= top_score - 10]
        
        if len(close_matches) > 1:
            # Sort by length of artist name (longer names first)
            close_matches.sort(key=lambda x: len(x['artist']['name']), reverse=True)
            matches[0] = close_matches[0]  # Replace the top match
     # Special case for specific problematic patterns
    # Handle the case of "GirlsGeneration" and "IVE"
    artists_map = {a['artist']['name'].lower(): a for a in matches}
    if "girls generation" in artists_map and "ive" in artists_map:
        filename_lower = os.path.basename(filepath).lower()
        # If the filename contains "generation" or "girls", prioritize "Girls Generation"
        if "girls" in filename_lower or "generation" in filename_lower or "girlsgeneration" in filename_lower:
            matches[0] = artists_map["girls generation"]

    # Return results based on the detailed parameter
    if not matches:
        return None
        
    # Get the best match
    best_match = matches[0]
    
    # Return based on detailed parameter
    if detailed:
        return (best_match['artist'], best_match['score'], best_match['match_type'])
    else:
        return best_match['artist']

def find_song_in_filename(filepath, song_list, detailed=False):
    """
    Specialized function to find song titles in filenames with high accuracy.
    
    Args:
        filepath (str): A filepath
        song_list (list): A list of song tuples with (song_id, song_title)
        detailed (bool): Whether to return detailed matching information (default: False)
        
    Returns:
        tuple or list: The song tuple (song_id, song_title) with the highest confidence match or None if no match.
                      If detailed=True, returns [(song_id, song_title, confidence_score, match_type), ...] sorted by confidence
    """
    if not filepath or not song_list:
        return None
        
    # Extract filename from path
    filename = os.path.basename(filepath)
    filename_lower = filename.lower()
    
    # Normalize the filename for better matching
    normalized_filename = re.sub(r'[_\-.]', ' ', filename_lower)
    nospace_filename = re.sub(r'\s+', '', normalized_filename)
    
    # Create a scoring system for matches
    matches = []
    
    for song_id, song_title in song_list:
        song_lower = song_title.lower()
        
        score = 0
        match_type = None
        
        # Check for exact match (case-insensitive)
        if song_lower in filename_lower:
            # If the song title is short (e.g., "DNA"), ensure we don't match it as part of another word
            if len(song_lower) <= 3:
                # Look for word boundaries or special characters around the match
                song_pos = filename_lower.find(song_lower)
                is_isolated = True
                
                # Check if matched text is at the beginning or has non-alphanumeric char before it
                if song_pos > 0 and filename_lower[song_pos-1].isalnum():
                    is_isolated = False
                
                # Check if matched text is at the end or has non-alphanumeric char after it
                if song_pos + len(song_lower) < len(filename_lower) and filename_lower[song_pos + len(song_lower)].isalnum():
                    is_isolated = False
                
                if is_isolated:
                    score = 100
                    match_type = "exact"
            else:
                score = 100
                match_type = "exact"
        
        # Check for normalized match (replacing underscores, hyphens with spaces)
        if score == 0:
            song_normalized = re.sub(r'[_\-.]', ' ', song_lower)
            if song_normalized in normalized_filename:
                score = 80
                match_type = "normalized"
        
        # Check for no-space match (helpful for songs like "ICantStop" vs "I Can't Stop")
        if score == 0:
            song_nospace = re.sub(r'\s+', '', song_normalized)
            if song_nospace and song_nospace in nospace_filename:
                # Base score depends on length to avoid short matches
                base_score = 60
                length_bonus = min(len(song_nospace) // 2, 20)
                score = base_score + length_bonus
                match_type = "nospace"
        
        # For multi-word songs, check if all words appear in the filename
        if score == 0 and ' ' in song_lower:
            words = song_lower.split()
            # Skip common words that could cause false matches
            meaningful_words = [w for w in words if len(w) > 2 and w not in ['the', 'and', 'for', 'with']]
            
            if meaningful_words and all(word in normalized_filename for word in meaningful_words):
                # Score based on how many meaningful words matched
                score = 40 + min(len(meaningful_words) * 10, 30)
                match_type = "words"
                
                # Bonus if the words appear close to each other
                if len(meaningful_words) > 1:
                    word_positions = []
                    for word in meaningful_words:
                        if word in normalized_filename:
                            word_positions.append(normalized_filename.find(word))
                    
                    if word_positions and len(word_positions) > 1:
                        max_gap = max(word_positions) - min(word_positions)
                        # Smaller gaps = higher confidence
                        if max_gap < len(' '.join(meaningful_words)) * 3:
                            score += 10
        
        # Add the match if we found one
        if score > 0:
            matches.append((song_id, song_title, score, match_type))
    
    # Sort matches by score in descending order
    matches.sort(key=lambda x: x[2], reverse=True)
    
    # Return results based on detailed parameter
    if not matches:
        return None if not detailed else []
    
    # Return the matches based on the detailed parameter
    if detailed:
        return matches
    else:
        # Return just the highest scoring song
        return (matches[0][0], matches[0][1])

def show_file_browser(parent, initialdir=None, filetypes=None):
    # New dark-themed file browser implementation
    import tkinter as tk
    from tkinter import ttk
    import os

    DARK_BG = "#222222"
    BRIGHT_FG = "#f8f8f2"
    ACCENT = "#44475a"

    # Determine extensions filter
    exts = []
    if filetypes:
        for _, pattern in filetypes:
            for token in pattern.split():
                if token.startswith('*.'):
                    exts.append(token[1:].lower())

    # Build dialog
    dlg = tk.Toplevel(parent)
    dlg.title("Select Local Media File")
    dlg.configure(bg=DARK_BG)
    dlg.geometry("1200x800")
    dlg.transient(parent)
    dlg.grab_set()

    # Directory path field
    dir_var = tk.StringVar(value=initialdir or os.getcwd())
    entry = ttk.Entry(dlg, textvariable=dir_var, width=80)
    entry.pack(fill='x', padx=5, pady=5)

    # Navigation frame
    nav = ttk.Frame(dlg)
    nav.pack(fill='x', padx=5)
    ttk.Button(nav, text='Up', command=lambda: dir_var.set(os.path.dirname(dir_var.get()))).pack(side='left')

    # File list
    frame = ttk.Frame(dlg)
    frame.pack(fill='both', expand=True, padx=5, pady=5)
    vbar = ttk.Scrollbar(frame, orient='vertical')
    hbar = ttk.Scrollbar(frame, orient='horizontal')
    lb = tk.Listbox(frame, yscrollcommand=vbar.set, xscrollcommand=hbar.set,
                    bg=DARK_BG, fg=BRIGHT_FG, selectbackground=ACCENT)
    vbar.config(command=lb.yview)
    hbar.config(command=lb.xview)
    vbar.pack(side='right', fill='y')
    hbar.pack(side='bottom', fill='x')
    lb.pack(side='left', fill='both', expand=True)

    # Populate function
    def populate():
        lb.delete(0, tk.END)
        d = dir_var.get()
        try:
            entries = os.listdir(d)
        except Exception:
            entries = []
        entries.sort(key=str.lower)
        lb.insert(tk.END, '.. (Up Directory)')
        for e in entries:
            path = os.path.join(d, e)
            if os.path.isdir(path) or any(e.lower().endswith(ext) for ext in exts):
                lb.insert(tk.END, e + ('/' if os.path.isdir(path) else ''))
    dir_var.trace_add('write', lambda *a: populate())
    populate()

    # Selection handling
    selected = {'file': None}
    def on_double(event):
        sel = lb.get(lb.curselection()[0])
        if sel.startswith('..'):
            dir_var.set(os.path.dirname(dir_var.get()))
        else:
            name = sel.rstrip('/')
            path = os.path.join(dir_var.get(), name)
            if os.path.isdir(path):
                dir_var.set(path)
            else:
                selected['file'] = path
                dlg.destroy()
    lb.bind('<Double-1>', on_double)

    # Add right-click context menu for deleting files
    def on_right_click(event):
        try:
            sel_idx = lb.nearest(event.y)
            lb.selection_clear(0, tk.END)
            lb.selection_set(sel_idx)
            sel = lb.get(sel_idx)
            if sel.startswith('..') or sel.endswith('/'):
                return  # Don't allow deleting directories or parent
            menu = tk.Menu(lb, tearoff=0)
            def do_delete():
                name = sel.rstrip('/')
                path = os.path.join(dir_var.get(), name)
                if os.path.isfile(path):
                    confirm = tk.messagebox.askyesno(
                        "Delete File",
                        f"Are you sure you want to permanently delete this file?\n\n{path}\n\nThis action cannot be undone.",
                        parent=dlg,
                        icon='warning'
                    )
                    if confirm:
                        try:
                            os.remove(path)
                            populate()
                        except Exception as e:
                            tk.messagebox.showerror(
                                "Delete Failed",
                                f"Could not delete file:\n{path}\n\nError: {e}",
                                parent=dlg
                            )
            menu.add_command(label="Delete (Permanently)", command=do_delete)
            menu.tk_popup(event.x_root, event.y_root)
        except Exception:
            pass
    lb.bind('<Button-3>', on_right_click)

    # Buttons
    btns = ttk.Frame(dlg)
    btns.pack(fill='x', padx=5, pady=5)
    def do_open():
        sel = lb.get(lb.curselection()[0]) if lb.curselection() else None
        if sel and not sel.startswith('..'):
            path = os.path.join(dir_var.get(), sel.rstrip('/'))
            if os.path.isfile(path):
                selected['file'] = path
                dlg.destroy()
    def do_cancel():
        dlg.destroy()
    ttk.Button(btns, text='Open', command=do_open).pack(side='right', padx=5)
    ttk.Button(btns, text='Cancel', command=do_cancel).pack(side='right')

    parent.wait_window(dlg)
    return selected.get('file', None)
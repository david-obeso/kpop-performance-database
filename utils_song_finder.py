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

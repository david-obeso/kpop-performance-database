#!/usr/bin/env python3
# test_artist_detection.py - Test the enhanced artist name detection functions

import os
import utils

print("Script started")

def test_find_artist_in_filename():
    """Test the artist detection in filenames with various formatting scenarios."""
    # Mock test data
    artists = [
        {'id': 1, 'name': 'Red Velvet'},
        {'id': 2, 'name': 'TWICE'},
        {'id': 3, 'name': 'Black Pink'},
        {'id': 4, 'name': 'IVE'},
        {'id': 5, 'name': 'Girls Generation'},
        {'id': 6, 'name': 'aespa'},
    ]
    
    # Test filenames
    test_files = [
        '220101_Red Velvet_Performance_Music Bank.mp4',
        '230502_TWICE_performance_MCountdown.mp4',
        '210317BlackPink-StageShow.mp4',
        '231225_IVE.mp4',
        '220908_GirlsGeneration_Anniversary.mp4',
        '230415aespa_NextLevel.mp4',
        '220707 Red.Velvet.Psycho.performance.mp4',
        '231112_redvelvet_feel_my_rhythm.mp4'
    ]
    
    print("Testing artist detection in filenames:")
    print("-" * 50)
    
    for filepath in test_files:
        print(f"Filepath: {filepath}")
        
        # Test the specialized artist detection function
        best_match = utils.find_artist_in_filename(filepath, artists)
        if best_match:
            print(f"Best match: {best_match['name']}")
        else:
            print("No artist match found.")
        
        # Test the original string matching function
        artist_names = [artist['name'] for artist in artists]
        string_matches = utils.find_string_in_filename(filepath, artist_names)
        if string_matches:
            print(f"String matches: {', '.join(string_matches)}")
        else:
            print("No string matches found.")
        
        print("-" * 50)

if __name__ == "__main__":
    test_find_artist_in_filename()

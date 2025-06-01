#!/usr/bin/env python3
# song_detection_test.py - Test the song detection capabilities

import os
import sys
import re
import utils

def test_song_detection():
    """Test the song detection in filenames with various formatting scenarios."""
    # Mock song data
    songs = [
        (1, "DNA"),
        (2, "Boy With Luv"),
        (3, "Dynamite"),
        (4, "Black Swan"),
        (5, "Blood Sweat & Tears"),
        (6, "Spring Day"),
        (7, "Butter"),
        (8, "Life Goes On"),
        (9, "I Can't Stop Me"),
        (10, "Feel My Rhythm")
    ]
    
    # Test filenames
    test_files = [
        '220101_BTS_DNA_Performance_Music Bank.mp4',
        '230502_BTS_Boy With Luv_MCountdown.mp4',
        '210317_Dynamite-BTS-StageShow.mp4',
        '231225_BTS_Black.Swan.mp4',
        '220908_Blood.Sweat.Tears_BTS_Anniversary.mp4',
        '230415_SpringDay_BTS_NextLevel.mp4',
        '220707 BTS Butter performance.mp4',
        '231112_twice_ICantStopMe_live.mp4',
        '231114_Red Velvet_Feel.My.Rhythm_Show.mp4',
        '230101_BTS_Concert_With_All_Songs.mp4'  # No specific song should be detected with high confidence
    ]
    
    print("Testing song detection in filenames:")
    print("=" * 60)
    print(f"Testing {len(test_files)} different filename patterns...\n")
    
    for filepath in test_files:
        print(f"Filepath: {filepath}")
        
        # Get detailed results
        result = utils.find_song_in_filename(filepath, songs, detailed=True)
        
        if result:
            print("Detected songs in order of confidence:")
            for song_id, song_title, score, match_type in result[:3]:  # Show top 3 matches
                print(f"  {song_title}: {score} points ({match_type})")
                
            # Get the highest confidence match
            best_match = utils.find_song_in_filename(filepath, songs)
            if best_match:
                song_id, song_title = best_match
                print(f"Best match: {song_title} (ID: {song_id})")
            else:
                print("No best match")
        else:
            print("No song matches found")
        
        print("-" * 60)

if __name__ == "__main__":
    test_song_detection()

#!/usr/bin/env python3
"""
comprehensive_test.py - Test script for the enhanced artist name detection functions

This script tests the enhanced artist name detection functionality, focusing on
multi-word artist names and potential edge cases.
"""

import os
import re
import utils

def test_artist_detection():
    """Test the artist detection functionality with various test cases."""
    # Define test artists
    artists = [
        {'id': 1, 'name': 'Red Velvet'},
        {'id': 2, 'name': 'TWICE'},
        {'id': 3, 'name': 'Black Pink'},
        {'id': 4, 'name': 'IVE'},
        {'id': 5, 'name': 'Girls Generation'},
        {'id': 6, 'name': 'aespa'},
        {'id': 7, 'name': 'NewJeans'},
        {'id': 8, 'name': 'ITZY'},
        {'id': 9, 'name': '(G)I-DLE'}
    ]
    
    # Define test cases with expected results
    test_cases = [
        # Format: (filename, expected_artist_id, description)
        ('220101_Red Velvet_Performance_Music Bank.mp4', 1, 'Standard case with spaces'),
        ('230502_TWICE_performance_MCountdown.mp4', 2, 'Standard case with underscore'),
        ('210317BlackPink-StageShow.mp4', 3, 'No spaces between words'),
        ('231225_IVE.mp4', 4, 'Single-word artist'),
        ('220908_GirlsGeneration_Anniversary.mp4', 5, 'Multi-word artist with no spaces'),
        ('230415aespa_NextLevel.mp4', 6, 'Single-word artist with no delimiter'),
        ('220707 Red.Velvet.Psycho.performance.mp4', 1, 'Words separated by periods'),
        ('231112_redvelvet_feel_my_rhythm.mp4', 1, 'Lowercase with underscore'),
        ('231114_Live_Show_with_IVE_Performance.mp4', 4, 'Artist name in middle of filename'),
        ('230101 Anniversary Special - Girls Generation.mp4', 5, 'Artist at end with dash separator'),
        ('230505 ITZY - WANNABE (Live).mp4', 8, 'Short artist name with surroundings'),
        ('230606 Festival LiveStream - NewJeans Performance.mp4', 7, 'CamelCase artist name'),
        ('230707-(G)I-DLE-TOMBOY.mp4', 9, 'Artist name with special characters'),
        ('230808_Live_Festival_Archive.mp4', None, 'No artist match expected'),
        ('240101_JiminIVEdanceMix.mp4', None, 'IVE as substring, should not match')
    ]
    
    print("Comprehensive Artist Name Detection Test")
    print("=" * 60)
    print(f"Testing {len(test_cases)} different filename patterns...")
    print()
    
    # Track successes and failures
    success_count = 0
    failures = []
    
    # Process each test case
    for idx, (filename, expected_artist_id, description) in enumerate(test_cases, 1):
        print(f"Test {idx}: {description}")
        print(f"Filename: {filename}")
        
        # Get detailed results
        result = utils.find_artist_in_filename(filename, artists, detailed=True)
        
        if result is None:
            best_match = None
            score = 0
            match_type = None
            matched_artist_id = None
        else:
            best_match, score, match_type = result
            matched_artist_id = best_match['id']
        
        # Print detailed results
        if best_match:
            print(f"Found: {best_match['name']} (ID: {best_match['id']})")
            print(f"Score: {score} | Match type: {match_type}")
        else:
            print("No artist match found")
        
        # Check if the result matches expectations
        success = (matched_artist_id == expected_artist_id)
        if success:
            print("✓ PASSED")
            success_count += 1
        else:
            print("✗ FAILED - Expected artist ID:", expected_artist_id)
            failures.append(idx)
        
        print("-" * 60)
    
    # Print summary
    print(f"\nTest Summary: {success_count}/{len(test_cases)} tests passed")
    if failures:
        print(f"Failed tests: {', '.join(map(str, failures))}")
    else:
        print("All tests passed successfully!")

if __name__ == "__main__":
    test_artist_detection()

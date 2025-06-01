#!/usr/bin/env python3

import os
import re
import sys

# Import relevant functions from utils.py
sys.path.append('/home/david/kpop-performance-database')
import utils

# Test data
artists = [
    {'id': 1, 'name': 'Red Velvet'},
    {'id': 2, 'name': 'TWICE'},
    {'id': 3, 'name': 'Black Pink'},
    {'id': 4, 'name': 'IVE'},
    {'id': 5, 'name': 'Girls Generation'},
    {'id': 6, 'name': 'aespa'},
]

# Test a single case
def test_single_case(filename):
    print(f"Testing file: {filename}")
    
    try:
        result = utils.find_artist_in_filename(filename, artists, detailed=True)
        
        if result:
            artist, score, match_type = result
            print(f"Match: {artist['name']} (ID: {artist['id']})")
            print(f"Score: {score}, Type: {match_type}")
        else:
            print("No match found")
    except Exception as e:
        print(f"Error: {str(e)}")

# Test a few cases
test_single_case('220908_GirlsGeneration_Anniversary.mp4')
test_single_case('231225_IVE.mp4')
test_single_case('240101_AnnIVErsary.mp4')  # Should not match IVE

print("\nOriginal find_string_in_filename results:")
artist_names = [a['name'] for a in artists]
for filename in ['220908_GirlsGeneration_Anniversary.mp4', '231225_IVE.mp4', '240101_AnnIVErsary.mp4']:
    matches = utils.find_string_in_filename(filename, artist_names)
    print(f"{filename}: {', '.join(matches) if matches else 'No matches'}")

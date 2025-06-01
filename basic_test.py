#!/usr/bin/env python3

import utils

# Define a few artists
artists = [
    {'id': 1, 'name': 'Red Velvet'},
    {'id': 4, 'name': 'IVE'},
    {'id': 5, 'name': 'Girls Generation'},
]

# Test cases
filenames = [
    "220908_GirlsGeneration_Anniversary.mp4",
    "231225_IVE.mp4"
]

# Test each file
for filename in filenames:
    print(f"Testing file: {filename}")
    match = utils.find_artist_in_filename(filename, artists)
    print(f"Best match: {match['name'] if match else 'No match found'}")
    print("-" * 40)

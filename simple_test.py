#!/usr/bin/env python3
# simple_test.py - A simple test to check if the artist detection works

import os
import sys
print("Python version:", sys.version)
print("Simple test script started")

import utils

# Test with one specific file
filename = "220908_GirlsGeneration_Anniversary.mp4"
artists = [
    {'id': 1, 'name': 'Red Velvet'},
    {'id': 2, 'name': 'TWICE'},
    {'id': 3, 'name': 'Black Pink'},
    {'id': 4, 'name': 'IVE'},
    {'id': 5, 'name': 'Girls Generation'},
    {'id': 6, 'name': 'aespa'},
]

print(f"Testing file: {filename}")
match = utils.find_artist_in_filename(filename, artists)
print(f"Best match: {match['name'] if match else 'No match'}")

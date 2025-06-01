#!/usr/bin/env python3
# quick_test.py - A quick test of artist detection

import utils

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

# Mock test data
artists = [
    {'id': 1, 'name': 'Red Velvet'},
    {'id': 2, 'name': 'TWICE'},
    {'id': 3, 'name': 'Black Pink'},
    {'id': 4, 'name': 'IVE'},
    {'id': 5, 'name': 'Girls Generation'},
    {'id': 6, 'name': 'aespa'},
]

for filepath in test_files:
    best_match = utils.find_artist_in_filename(filepath, artists)
    print(f"File: {filepath}")
    print(f"Best match: {best_match['name'] if best_match else 'None'}")
    print("-" * 40)

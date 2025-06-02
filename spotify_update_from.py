import spotipy
from spotipy.oauth2 import SpotifyOAuth
import sqlite3
import os
import json
import time
from datetime import datetime

# --- Configuration ---
DB_FILE = "kpop_database.db"
# CREDENTIALS_FILE_PATH should be a plain text file:
# Line 1: SPOTIPY_CLIENT_ID
# Line 2: SPOTIPY_CLIENT_SECRET
CREDENTIALS_FILE_PATH = os.path.expanduser("~/.spotify_credentials")
STATE_FILE_PATH = "spotify_album_sync_state.json" # Stores the last offset for current run
SPOTIPY_REDIRECT_URI = "http://127.0.0.1:8888/callback"
API_SCOPE = "user-library-read"

# --- API Call Delays (seconds) ---
DELAY_PER_PAGE = 10            # Delay after fetching a page of saved albums
DELAY_PER_ALBUM_DETAILS = 5  # Delay after fetching tracks for an album or individual artist
DELAY_PER_ARTIST_BATCH = 5   # Delay after fetching a batch of artists

# --- Retry/Backoff Helper ---
RETRY_ATTEMPTS = 5
RETRY_BASE_DELAY = 5  # seconds

def fetch_with_retries(sp_function, *args, **kwargs):
    """Spotify API call with retry/backoff on 429 and server errors."""
    for attempt in range(RETRY_ATTEMPTS):
        try:
            return sp_function(*args, **kwargs)
        except spotipy.SpotifyException as e:
            if e.http_status == 429:
                retry_after = int(e.headers.get('Retry-After', RETRY_BASE_DELAY * (attempt + 1)))
                print(f"Rate limited. Retrying after {retry_after} seconds...")
                time.sleep(retry_after + 1)
            elif e.http_status >= 500:
                print(f"Spotify server error ({e.http_status}). Retrying in {RETRY_BASE_DELAY * (attempt + 1)}s...")
                time.sleep(RETRY_BASE_DELAY * (attempt + 1))
            else:
                print(f"Unrecoverable Spotify API error: {e}")
                raise
        except Exception as e:
            print(f"Network or unexpected error: {e}. Retrying in {RETRY_BASE_DELAY * (attempt + 1)}s...")
            time.sleep(RETRY_BASE_DELAY * (attempt + 1))
    print(f"Failed to execute {sp_function.__name__} after {RETRY_ATTEMPTS} retries.")
    return None

# --- Helper Functions ---
def load_credentials():
    """
    Loads Spotify API credentials from a plain text file.
    Expects client ID on the first line and client secret on the second.
    """
    if not os.path.exists(CREDENTIALS_FILE_PATH):
        print(f"Error: Credentials file not found at {CREDENTIALS_FILE_PATH}")
        print("Please create it with your SPOTIPY_CLIENT_ID on the first line and SPOTIPY_CLIENT_SECRET on the second line.")
        return None, None
    try:
        with open(CREDENTIALS_FILE_PATH, 'r') as f:
            lines = f.readlines()
            if len(lines) < 2:
                print(f"Error: Credentials file {CREDENTIALS_FILE_PATH} is not formatted correctly.")
                print("Expected client ID on line 1 and client secret on line 2.")
                return None, None
            
            client_id = lines[0].strip()
            client_secret = lines[1].strip()
            
            if not client_id or not client_secret:
                print(f"Error: Client ID or Client Secret is empty in {CREDENTIALS_FILE_PATH}.")
                return None, None
            return client_id, client_secret
    except Exception as e:
        print(f"Error reading credentials file {CREDENTIALS_FILE_PATH}: {e}")
        return None, None

def get_spotify_client(client_id, client_secret):
    """Authenticates with Spotify and returns a Spotipy client instance."""
    try:
        auth_manager = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=SPOTIPY_REDIRECT_URI,
            scope=API_SCOPE,
            cache_path=".spotifycache" 
        )
        sp = spotipy.Spotify(auth_manager=auth_manager)
        sp.me() 
        print("Successfully authenticated with Spotify.")
        return sp
    except Exception as e:
        print(f"Spotify authentication failed: {e}")
        print("Please ensure your credentials are correct, the redirect URI is configured in your Spotify App,")
        print("and you have an internet connection.")
        return None

def db_connect():
    """Connects to the SQLite database."""
    return sqlite3.connect(DB_FILE)

def setup_database(conn):
    """Creates database tables if they don't already exist. Safe for existing DBs."""
    cursor = conn.cursor()
    # Schema as per user's latest correction (no genres in artists, no is_explicit in songs)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS "artists" (
        "artist_id" INTEGER PRIMARY KEY AUTOINCREMENT,
        "artist_name" TEXT NOT NULL UNIQUE,
        "spotify_artist_id" TEXT UNIQUE,
        "artist_image_url" TEXT,
        "popularity" INTEGER,
        "followers_total" INTEGER,
        "spotify_artist_uri" TEXT,
        "last_checked_at" TEXT
    )''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS "albums" (
        "album_id" INTEGER PRIMARY KEY AUTOINCREMENT,
        "album_title" TEXT NOT NULL,
        "spotify_album_id" TEXT UNIQUE NOT NULL,
        "album_type" TEXT,
        "total_tracks" INTEGER,
        "release_date" TEXT,
        "release_date_precision" TEXT,
        "label" TEXT,
        "popularity" INTEGER,
        "cover_image_url" TEXT,
        "spotify_album_uri" TEXT,
        "spotify_added_at" TEXT NOT NULL,
        "last_checked_at" TEXT
    )''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS "songs" (
        "song_id" INTEGER PRIMARY KEY AUTOINCREMENT,
        "song_title" TEXT NOT NULL,
        "spotify_song_id" TEXT UNIQUE NOT NULL,
        "duration_ms" INTEGER,
        "spotify_track_uri" TEXT,
        "last_checked_at" TEXT
    )''') # Removed "is_explicit" column
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS "album_artist_link_simplified" (
        "album_id" INTEGER NOT NULL,
        "artist_id" INTEGER NOT NULL,
        "artist_order" INTEGER DEFAULT 1,
        PRIMARY KEY ("album_id", "artist_id"),
        FOREIGN KEY ("album_id") REFERENCES "albums"("album_id") ON DELETE CASCADE,
        FOREIGN KEY ("artist_id") REFERENCES "artists"("artist_id") ON DELETE CASCADE
    )''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS "song_artist_link" (
        "song_id" INTEGER NOT NULL,
        "artist_id" INTEGER NOT NULL,
        "artist_order" INTEGER DEFAULT 1,
        PRIMARY KEY ("song_id", "artist_id"),
        FOREIGN KEY ("song_id") REFERENCES "songs"("song_id") ON DELETE CASCADE,
        FOREIGN KEY ("artist_id") REFERENCES "artists"("artist_id") ON DELETE CASCADE
    )''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS "song_album_link" (
        "song_id" INTEGER NOT NULL,
        "album_id" INTEGER NOT NULL,
        "track_number" INTEGER NOT NULL,
        "disc_number" INTEGER DEFAULT 1,
        PRIMARY KEY ("song_id", "album_id"),
        FOREIGN KEY ("song_id") REFERENCES "songs"("song_id") ON DELETE CASCADE,
        FOREIGN KEY ("album_id") REFERENCES "albums"("album_id") ON DELETE CASCADE
    )''')
    conn.commit()

def load_sync_state():
    if os.path.exists(STATE_FILE_PATH):
        try:
            with open(STATE_FILE_PATH, 'r') as f:
                state = json.load(f)
                return state.get("offset", 0)
        except json.JSONDecodeError:
            print(f"Warning: State file {STATE_FILE_PATH} is corrupted. Starting from offset 0.")
            return 0
    return 0

def save_sync_state(offset):
    try:
        with open(STATE_FILE_PATH, 'w') as f:
            json.dump({"offset": offset}, f)
    except IOError as e:
        print(f"Warning: Could not save sync state to {STATE_FILE_PATH}: {e}")

def get_last_known_added_at(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(spotify_added_at) FROM albums")
    result = cursor.fetchone()
    return result[0] if result and result[0] else None

def get_album_db_id_by_spotify_id(conn, spotify_album_id):
    cursor = conn.cursor()
    cursor.execute("SELECT album_id FROM albums WHERE spotify_album_id = ?", (spotify_album_id,))
    result = cursor.fetchone()
    return result[0] if result else None

def get_artist_db_id(conn, spotify_artist_id=None, artist_name=None):
    cursor = conn.cursor()
    if spotify_artist_id:
        cursor.execute("SELECT artist_id FROM artists WHERE spotify_artist_id = ?", (spotify_artist_id,))
    elif artist_name:
        cursor.execute("SELECT artist_id FROM artists WHERE artist_name = ?", (artist_name,))
    else:
        return None
    result = cursor.fetchone()
    return result[0] if result else None

def get_song_db_id(conn, spotify_song_id):
    cursor = conn.cursor()
    cursor.execute("SELECT song_id FROM songs WHERE spotify_song_id = ?", (spotify_song_id,))
    result = cursor.fetchone()
    return result[0] if result else None

def insert_or_update_artist(conn, artist_data, current_time_iso):
    cursor = conn.cursor()
    db_artist_id = get_artist_db_id(conn, spotify_artist_id=artist_data.get('id'))

    artist_name = artist_data.get('name')
    spotify_artist_id = artist_data.get('id')
    image_url = artist_data['images'][0]['url'] if artist_data.get('images') else None
    popularity = artist_data.get('popularity')
    followers = artist_data['followers']['total'] if artist_data.get('followers') else None
    uri = artist_data.get('uri')

    if db_artist_id:
        cursor.execute("""
            UPDATE artists
            SET artist_name = ?, artist_image_url = ?, popularity = ?,
                followers_total = ?, spotify_artist_uri = ?, last_checked_at = ?
            WHERE artist_id = ?
        """, (
            artist_name, image_url, popularity,
            followers, uri, current_time_iso,
            db_artist_id
        ))
    else:
        cursor.execute("""
            INSERT INTO artists (artist_name, spotify_artist_id, artist_image_url,
                                 popularity, followers_total, spotify_artist_uri, last_checked_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            artist_name, spotify_artist_id, image_url,
            popularity, followers, uri, current_time_iso
        ))
        db_artist_id = cursor.lastrowid
        print(f"Inserted new artist: {artist_name} (Spotify ID: {spotify_artist_id})")
    return db_artist_id

def insert_album(conn, album_item, current_time_iso):
    album_data = album_item['album']
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO albums (album_title, spotify_album_id, album_type, total_tracks,
                            release_date, release_date_precision, label, popularity,
                            cover_image_url, spotify_album_uri, spotify_added_at, last_checked_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        album_data['name'], album_data['id'], album_data['album_type'],
        album_data['total_tracks'], album_data['release_date'],
        album_data['release_date_precision'], album_data.get('label', ''),
        album_data.get('popularity'),
        album_data['images'][0]['url'] if album_data.get('images') else None,
        album_data['uri'], album_item['added_at'], current_time_iso
    ))
    print(f"Inserted album: {album_data['name']} (Spotify ID: {album_data['id']})")
    return cursor.lastrowid

def insert_song(conn, track_data, current_time_iso):
    cursor = conn.cursor()
    db_song_id = get_song_db_id(conn, track_data['id'])
    
    song_title = track_data['name']
    spotify_song_id = track_data['id']
    duration_ms = track_data['duration_ms']
    uri = track_data['uri']

    if db_song_id:
        cursor.execute("UPDATE songs SET last_checked_at = ? WHERE song_id = ?", (current_time_iso, db_song_id))
    else:
        cursor.execute("""
            INSERT INTO songs (song_title, spotify_song_id, duration_ms,
                               spotify_track_uri, last_checked_at)
            VALUES (?, ?, ?, ?, ?)
        """, ( 
            song_title, spotify_song_id, duration_ms,
            uri, current_time_iso
        ))
        db_song_id = cursor.lastrowid
        print(f"  Inserted song: {song_title} (Spotify ID: {spotify_song_id})")
    return db_song_id

def link_album_artist(conn, album_db_id, artist_db_id, order):
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO album_artist_link_simplified (album_id, artist_id, artist_order)
        VALUES (?, ?, ?)
    """, (album_db_id, artist_db_id, order))

def link_song_artist(conn, song_db_id, artist_db_id, order):
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO song_artist_link (song_id, artist_id, artist_order)
        VALUES (?, ?, ?)
    """, (song_db_id, artist_db_id, order))

def link_song_album(conn, song_db_id, album_db_id, track_number, disc_number):
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO song_album_link (song_id, album_id, track_number, disc_number)
        VALUES (?, ?, ?, ?)
    """, (song_db_id, album_db_id, track_number, disc_number))

# --- Main Sync Logic ---
def main():
    print("Starting Spotify album sync process...")
    client_id, client_secret = load_credentials()
    if not client_id or not client_secret:
        print("Exiting due to missing credentials.")
        return

    sp = get_spotify_client(client_id, client_secret)
    if not sp:
        print("Exiting due to Spotify authentication failure.")
        return

    conn = None
    try:
        conn = db_connect()
        setup_database(conn) 
        print(f"Database '{DB_FILE}' connected and schema ensured.")

        last_db_added_at = get_last_known_added_at(conn)
        print(f"Last known album added_at in DB: {last_db_added_at if last_db_added_at else 'None (first sync?)'}")

        offset = load_sync_state()
        limit = 20
        new_albums_processed_count = 0
        
        fetched_artist_details_map_this_run = {} 

        while True:
            current_time_iso = datetime.utcnow().isoformat() + "Z"
            print(f"\nFetching page of saved albums from Spotify. Offset: {offset}, Limit: {limit}")
            results = fetch_with_retries(sp.current_user_saved_albums, limit=limit, offset=offset)
            if results is None:
                print("Failed to fetch saved albums after retries. Exiting.")
                break

            if not results or not results['items']:
                print("No more albums found in Spotify library for this page or at all.")
                break

            stop_processing_older_albums = False
            albums_on_this_page = results['items']
            albums_to_process_fully = []
            artist_spotify_ids_to_fetch_on_this_page = set()

            for item in albums_on_this_page:
                album_spotify_id = item['album']['id']
                album_added_at = item['added_at']

                if last_db_added_at and album_added_at <= last_db_added_at:
                    print(f"  Album '{item['album']['name']}' (added {album_added_at}) is older or same as last sync ({last_db_added_at}). Will stop after this page.")
                    stop_processing_older_albums = True
                
                if get_album_db_id_by_spotify_id(conn, album_spotify_id):
                    print(f"  Album '{item['album']['name']}' (ID: {album_spotify_id}) already in DB. Skipping this specific album.")
                    continue 
                
                albums_to_process_fully.append(item)
                for artist_summary in item['album'].get('artists', []):
                    artist_id = artist_summary.get('id')
                    if artist_id and artist_id not in fetched_artist_details_map_this_run:
                        artist_spotify_ids_to_fetch_on_this_page.add(artist_id)

            if artist_spotify_ids_to_fetch_on_this_page:
                artist_ids_list = list(artist_spotify_ids_to_fetch_on_this_page)
                for i in range(0, len(artist_ids_list), 50): 
                    batch_ids = artist_ids_list[i:i+50]
                    print(f"Fetching details for {len(batch_ids)} album artists (batch {i//50 + 1})...")
                    artist_details_results = fetch_with_retries(sp.artists, artists=batch_ids)
                    if artist_details_results and artist_details_results['artists']:
                        for artist_data in artist_details_results['artists']:
                            if artist_data: 
                                fetched_artist_details_map_this_run[artist_data['id']] = artist_data

            for item in albums_to_process_fully:
                album_data_api = item['album']
                print(f"\nProcessing new album: '{album_data_api['name']}' (Added: {item['added_at']})")
                try:
                    conn.execute("BEGIN TRANSACTION")
                    album_db_id = insert_album(conn, item, current_time_iso)
                    new_albums_processed_count += 1
                    for i, artist_summary in enumerate(album_data_api.get('artists', [])):
                        artist_spotify_id = artist_summary.get('id')
                        artist_data_full = fetched_artist_details_map_this_run.get(artist_spotify_id)
                        if not artist_data_full and artist_spotify_id: 
                            print(f"  Warning: Album artist '{artist_summary.get('name')}' (ID: {artist_spotify_id}) details not in pre-fetch. Fetching individually.")
                            artist_data_full = fetch_with_retries(sp.artist, artist_spotify_id)
                            if artist_data_full:
                                fetched_artist_details_map_this_run[artist_spotify_id] = artist_data_full 
                        if artist_data_full:
                            artist_db_id = insert_or_update_artist(conn, artist_data_full, current_time_iso)
                            if artist_db_id:
                               link_album_artist(conn, album_db_id, artist_db_id, i + 1)
                        elif artist_summary.get('name'): 
                            artist_db_id_by_name = get_artist_db_id(conn, artist_name=artist_summary.get('name'))
                            if artist_db_id_by_name:
                                 link_album_artist(conn, album_db_id, artist_db_id_by_name, i + 1)
                            else:
                                print(f"  Could not resolve album artist '{artist_summary.get('name')}' for link (no Spotify ID and not in DB by name).")

                    print(f"  Fetching tracks for album: '{album_data_api['name']}'...")
                    album_tracks_paginator = fetch_with_retries(sp.album_tracks, album_data_api['id'], limit=50)
                    if album_tracks_paginator is None:
                        print(f"  Error fetching initial tracks for album '{album_data_api['name']}'. Skipping album.")
                        conn.rollback() 
                        continue 

                    album_tracks_data_for_processing = []
                    song_artist_spotify_ids_for_this_album_to_fetch = set()
                    temp_tracks = []
                    if album_tracks_paginator:
                        temp_tracks.extend(album_tracks_paginator['items'])
                        while album_tracks_paginator and album_tracks_paginator['next']:
                            print(f"    Fetching next page of tracks for '{album_data_api['name']}'...")
                            album_tracks_paginator = fetch_with_retries(sp.next, album_tracks_paginator)
                            if album_tracks_paginator:
                                temp_tracks.extend(album_tracks_paginator['items'])
                            else:
                                break
                    for track_item_api in temp_tracks:
                        if not track_item_api or not track_item_api.get('id'): 
                            print(f"    Skipping track without ID or data (e.g., local file): {track_item_api.get('name') if track_item_api else 'N/A'}")
                            continue
                        album_tracks_data_for_processing.append(track_item_api)
                        for artist_summary in track_item_api.get('artists', []):
                            artist_id = artist_summary.get('id')
                            if artist_id and artist_id not in fetched_artist_details_map_this_run: 
                                song_artist_spotify_ids_for_this_album_to_fetch.add(artist_id)
                    if song_artist_spotify_ids_for_this_album_to_fetch:
                        song_artist_ids_list = list(song_artist_spotify_ids_for_this_album_to_fetch)
                        for i in range(0, len(song_artist_ids_list), 50):
                            batch_ids = song_artist_ids_list[i:i+50]
                            print(f"    Fetching details for {len(batch_ids)} song artists (batch {i//50 + 1})...")
                            artist_details_results = fetch_with_retries(sp.artists, artists=batch_ids)
                            if artist_details_results and artist_details_results['artists']:
                                for artist_data in artist_details_results['artists']:
                                    if artist_data:
                                        fetched_artist_details_map_this_run[artist_data['id']] = artist_data
                    for track_item_api in album_tracks_data_for_processing:
                        song_db_id = insert_song(conn, track_item_api, current_time_iso) 
                        if song_db_id:
                            link_song_album(conn, song_db_id, album_db_id,
                                            track_item_api['track_number'], track_item_api.get('disc_number', 1))
                            for j, song_artist_summary in enumerate(track_item_api.get('artists', [])):
                                artist_spotify_id = song_artist_summary.get('id')
                                artist_data_full = fetched_artist_details_map_this_run.get(artist_spotify_id)

                                if not artist_data_full and artist_spotify_id: 
                                    print(f"    Warning: Song artist '{song_artist_summary.get('name')}' (ID: {artist_spotify_id}) details not pre-fetched. Fetching individually.")
                                    artist_data_full = fetch_with_retries(sp.artist, artist_spotify_id)
                                    if artist_data_full:
                                        fetched_artist_details_map_this_run[artist_spotify_id] = artist_data_full
                                
                                if artist_data_full:
                                    artist_db_id = insert_or_update_artist(conn, artist_data_full, current_time_iso)
                                    if artist_db_id:
                                        link_song_artist(conn, song_db_id, artist_db_id, j + 1)
                                elif song_artist_summary.get('name'):
                                    artist_db_id_by_name = get_artist_db_id(conn, artist_name=song_artist_summary.get('name'))
                                    if artist_db_id_by_name:
                                        link_song_artist(conn, song_db_id, artist_db_id_by_name, j + 1)
                                    else:
                                        print(f"    Could not resolve song artist '{song_artist_summary.get('name')}' for link.")
                    conn.commit()
                    print(f"  Successfully processed and committed album: '{album_data_api['name']}'")
                except Exception as e_album_proc:
                    if conn: conn.rollback() 
                    print(f"  MAJOR ERROR processing album '{album_data_api.get('name', 'Unknown Album')}': {e_album_proc}. Rolled back changes for this album.")
            if stop_processing_older_albums:
                print("Stopping sync as older albums (based on added_at) have been reached on this page.")
                break
            offset += len(albums_on_this_page)
            save_sync_state(offset) 
            if not results['next']: 
                print("Reached end of Spotify library pages.")
                break
        save_sync_state(0) 
        print(f"\nSync finished. Processed {new_albums_processed_count} new albums in this session.")

    except sqlite3.Error as e_db:
        print(f"Database error: {e_db}")
        if conn:
            conn.rollback() 
    except Exception as e_main:
        print(f"An unexpected error occurred in main: {e_main}")
    finally:
        if conn:
            conn.close()
            print("Database connection closed.")

if __name__ == "__main__":
    main()
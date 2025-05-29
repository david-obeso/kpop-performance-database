import spotipy
from spotipy.oauth2 import SpotifyOAuth
import sqlite3
import os
import time
import json
from datetime import datetime, timezone

# --- Configuration ---
DB_FILE = "spotify_data.db"
CREDENTIALS_FILE_PATH = os.path.expanduser("~/.spotify_credentials")
# New state file for song synchronization
SONG_SYNC_STATE_FILE_PATH = "spotify_song_sync_state.json"
SPOTIPY_REDIRECT_URI = "http://localhost:8888/callback"
# Scope user-library-read is usually enough, but some track details might benefit
# from other scopes if you extend this later. For basic track info, it's fine.
API_SCOPE = "user-library-read"

# API call settings
ITEMS_PER_PAGE_SONGS = 50  # Max for album_tracks
DELAY_BETWEEN_ALBUM_PROCESSING = 1 # Seconds to wait after processing all songs for one album
DELAY_BETWEEN_SONG_PAGES = 1   # Seconds to wait between fetching pages of songs for a single album
RETRY_ATTEMPTS = 5
RETRY_BASE_DELAY = 5  # Seconds

# --- Helper Functions (many are similar to the album script) ---
def get_current_utc_iso_timestamp():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')

def load_credentials(file_path):
    try:
        with open(file_path, 'r') as f:
            client_id = f.readline().strip()
            client_secret = f.readline().strip()
        if not client_id or not client_secret:
            raise ValueError("Client ID or Secret not found.")
        return client_id, client_secret
    except FileNotFoundError:
        print(f"ERROR: Credentials file not found at {file_path}")
        exit(1)
    except ValueError as ve:
        print(f"ERROR: Reading credentials: {ve}")
        exit(1)

def load_last_processed_album_id(state_file_path):
    if os.path.exists(state_file_path):
        try:
            with open(state_file_path, 'r') as f:
                state = json.load(f)
                return state.get('last_processed_album_db_id', 0) # Default to 0 if key missing
        except json.JSONDecodeError:
            print(f"Warning: State file {state_file_path} corrupted. Starting from scratch.")
            return 0
    return 0 # No state file, start from the beginning

def save_last_processed_album_id(state_file_path, album_db_id):
    with open(state_file_path, 'w') as f:
        json.dump({'last_processed_album_db_id': album_db_id}, f)

def get_db_connection(db_file):
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

# --- Database Interaction Functions ---

# Artist functions (can be reused or slightly adapted if needed)
def get_artist_db_id_by_spotify_id(cursor, spotify_artist_id):
    cursor.execute("SELECT artist_id FROM artists WHERE spotify_artist_id = ?", (spotify_artist_id,))
    row = cursor.fetchone()
    return row['artist_id'] if row else None

def insert_artist(cursor, artist_details):
    sql = """
        INSERT INTO artists (
            artist_name, spotify_artist_id, spotify_artist_uri, last_checked_at
        ) VALUES (?, ?, ?, ?)
    """
    try:
        current_time = get_current_utc_iso_timestamp()
        cursor.execute(sql, (
            artist_details['artist_name'],
            artist_details['spotify_artist_id'],
            artist_details['spotify_artist_uri'],
            current_time
        ))
        return cursor.lastrowid
    except sqlite3.IntegrityError as e:
        print(f"Error inserting artist {artist_details['spotify_artist_id']} ({artist_details['artist_name']}): {e}. Likely exists or name conflict.")
        # Attempt to refetch, in case it was a name conflict but spotify_id already exists
        existing_id = get_artist_db_id_by_spotify_id(cursor, artist_details['spotify_artist_id'])
        if existing_id:
            print(f"  Found existing artist ID {existing_id} for spotify_artist_id {artist_details['spotify_artist_id']} after insert error.")
            return existing_id
        return None


# Song functions
def get_song_db_id_by_spotify_id(cursor, spotify_song_id):
    cursor.execute("SELECT song_id FROM songs WHERE spotify_song_id = ?", (spotify_song_id,))
    row = cursor.fetchone()
    return row['song_id'] if row else None

def insert_song(cursor, song_details):
    sql = """
        INSERT INTO songs (
            song_title, spotify_song_id, duration_ms, is_explicit,
            spotify_track_uri, last_checked_at
        ) VALUES (?, ?, ?, ?, ?, ?)
    """
    try:
        cursor.execute(sql, (
            song_details['song_title'],
            song_details['spotify_song_id'],
            song_details['duration_ms'],
            song_details['is_explicit'],
            song_details['spotify_track_uri'],
            song_details['last_checked_at']
        ))
        return cursor.lastrowid
    except sqlite3.IntegrityError as e:
        print(f"Error inserting song {song_details['spotify_song_id']}: {e}")
        return None

# Link table functions
def insert_song_album_link(cursor, song_db_id, album_db_id, track_number, disc_number):
    sql = """
        INSERT OR IGNORE INTO song_album_link (
            song_id, album_id, track_number, disc_number
        ) VALUES (?, ?, ?, ?)
    """
    try:
        cursor.execute(sql, (song_db_id, album_db_id, track_number, disc_number))
    except sqlite3.IntegrityError as e:
        # This shouldn't happen with INSERT OR IGNORE if PK is (song_id, album_id)
        print(f"Error inserting song-album link for song_id {song_db_id}, album_id {album_db_id}: {e}")

def insert_song_artist_link(cursor, song_db_id, artist_db_id, artist_order):
    sql = """
        INSERT OR IGNORE INTO song_artist_link (
            song_id, artist_id, artist_order
        ) VALUES (?, ?, ?)
    """
    try:
        cursor.execute(sql, (song_db_id, artist_db_id, artist_order))
    except sqlite3.IntegrityError as e:
        # This shouldn't happen with INSERT OR IGNORE if PK is (song_id, artist_id)
        print(f"Error inserting song-artist link for song_id {song_db_id}, artist_id {artist_db_id}: {e}")


def fetch_with_retries(sp_function, *args, **kwargs):
    """Generic wrapper for Spotipy calls with retry logic."""
    for attempt in range(RETRY_ATTEMPTS):
        try:
            return sp_function(*args, **kwargs)
        except spotipy.SpotifyException as e:
            if e.http_status == 429: # Rate limit
                retry_after = e.headers.get('Retry-After', RETRY_BASE_DELAY * (attempt + 1))
                print(f"Rate limited. Retrying after {retry_after} seconds...")
                time.sleep(int(retry_after) + 1)
            elif e.http_status >= 500: # Server error
                print(f"Spotify server error ({e.http_status}). Retrying in {RETRY_BASE_DELAY * (attempt + 1)}s...")
                time.sleep(RETRY_BASE_DELAY * (attempt + 1))
            else:
                print(f"Unrecoverable Spotify API error: {e}")
                raise # Re-raise for outer handling if needed
        except Exception as e: # Other errors like requests.exceptions.ConnectionError
            print(f"Network or unexpected error: {e}. Retrying in {RETRY_BASE_DELAY * (attempt + 1)}s...")
            time.sleep(RETRY_BASE_DELAY * (attempt + 1))
    print(f"Failed to execute {sp_function.__name__} after {RETRY_ATTEMPTS} retries.")
    return None

# --- Main Script ---
def main():
    client_id, client_secret = load_credentials(CREDENTIALS_FILE_PATH)
    auth_manager = SpotifyOAuth(client_id=client_id, client_secret=client_secret,
                                redirect_uri=SPOTIPY_REDIRECT_URI, scope=API_SCOPE)
    sp = spotipy.Spotify(auth_manager=auth_manager)

    try:
        user = sp.current_user()
        print(f"Authenticated with Spotify as: {user['display_name']} ({user['id']})")
    except Exception as e:
        print(f"Error during Spotify authentication: {e}")
        exit(1)

    conn = get_db_connection(DB_FILE)
    cursor = conn.cursor()

    last_processed_album_db_id = load_last_processed_album_id(SONG_SYNC_STATE_FILE_PATH)
    print(f"Starting song sync. Resuming after album DB ID: {last_processed_album_db_id}")

    # Get albums from DB that haven't been processed yet for songs
    # Order by album_id to ensure consistent processing order for resumability
    cursor.execute("""
        SELECT album_id, spotify_album_id, album_title FROM albums
        WHERE album_id > ?
        ORDER BY album_id ASC
    """, (last_processed_album_db_id,))
    
    albums_to_process = cursor.fetchall()

    if not albums_to_process:
        print("No new albums found to process for songs.")
        conn.close()
        return

    print(f"Found {len(albums_to_process)} albums to process for songs.")

    total_songs_added_session = 0
    total_artists_added_session = 0 # Artists added via songs

    for db_album in albums_to_process:
        album_db_id = db_album['album_id']
        album_spotify_id = db_album['spotify_album_id']
        album_title = db_album['album_title']
        print(f"\nProcessing album: '{album_title}' (DB ID: {album_db_id}, Spotify ID: {album_spotify_id})")

        current_song_offset = 0
        album_songs_processed_count = 0
        album_new_songs_added = 0
        album_new_artists_added = 0

        while True:
            print(f"  Fetching songs for album '{album_title}', page offset: {current_song_offset}")
            
            api_album_tracks = fetch_with_retries(
                sp.album_tracks,
                album_id=album_spotify_id,
                limit=ITEMS_PER_PAGE_SONGS,
                offset=current_song_offset
            )

            if api_album_tracks is None:
                print(f"  Failed to fetch tracks for album '{album_title}' after retries. Skipping this album.")
                # This album will be retried next time the script runs due to state saving.
                # Or, you could implement a more sophisticated error state for specific albums.
                conn.close() # Close connection before exiting if fatal error
                exit(1) # Or `break` to try next album if that's preferred for non-fatal.

            if not api_album_tracks['items']:
                print(f"  No more songs found for album '{album_title}'.")
                break # Finished with this album's songs

            for api_song_simple in api_album_tracks['items']:
                if api_song_simple is None or api_song_simple['id'] is None: # Skip if track is unavailable (e.g. local file or removed)
                    print(f"  Skipping an unavailable track in album '{album_title}'.")
                    album_songs_processed_count += 1
                    continue

                song_spotify_id = api_song_simple['id']
                
                # Check if song already exists
                song_db_id = get_song_db_id_by_spotify_id(cursor, song_spotify_id)

                if not song_db_id:
                    song_data_to_insert = {
                        'song_title': api_song_simple['name'],
                        'spotify_song_id': song_spotify_id,
                        'duration_ms': api_song_simple['duration_ms'],
                        'is_explicit': 1 if api_song_simple['explicit'] else 0,
                        'spotify_track_uri': api_song_simple['uri'],
                        'last_checked_at': get_current_utc_iso_timestamp()
                    }
                    song_db_id = insert_song(cursor, song_data_to_insert)
                    if song_db_id:
                        print(f"    Added song: '{song_data_to_insert['song_title']}' (Spotify ID: {song_spotify_id}) to DB (New ID: {song_db_id}).")
                        total_songs_added_session += 1
                        album_new_songs_added += 1
                    else:
                        print(f"    Failed to insert song '{api_song_simple['name']}'. Skipping links for this song.")
                        album_songs_processed_count += 1
                        continue # Skip artists and album link if song insertion failed
                # else:
                    # print(f"    Song '{api_song_simple['name']}' (Spotify ID: {song_spotify_id}) already in DB (ID: {song_db_id}).")
                    # Optionally update last_checked_at for existing song here

                # Link song to album
                insert_song_album_link(cursor, song_db_id, album_db_id,
                                       api_song_simple['track_number'],
                                       api_song_simple.get('disc_number', 1)) # API usually provides disc_number

                # Process song artists
                for order_idx, api_artist_summary in enumerate(api_song_simple['artists']):
                    artist_order = order_idx + 1
                    artist_spotify_id = api_artist_summary['id']
                    
                    artist_db_id = get_artist_db_id_by_spotify_id(cursor, artist_spotify_id)
                    
                    if not artist_db_id:
                        artist_data_to_insert = {
                            'artist_name': api_artist_summary['name'],
                            'spotify_artist_id': artist_spotify_id,
                            'spotify_artist_uri': api_artist_summary['uri']
                        }
                        artist_db_id = insert_artist(cursor, artist_data_to_insert)
                        if artist_db_id:
                            print(f"      Added artist (from song): '{artist_data_to_insert['artist_name']}' (Spotify ID: {artist_spotify_id}) to DB (New ID: {artist_db_id}).")
                            total_artists_added_session += 1
                            album_new_artists_added +=1
                        else:
                            print(f"      Failed to insert artist '{api_artist_summary['name']}' from song. Skipping link.")
                            continue # Skip linking this artist for this song
                    
                    if artist_db_id: # Ensure artist_db_id is valid
                        insert_song_artist_link(cursor, song_db_id, artist_db_id, artist_order)
                
                album_songs_processed_count += 1

            current_song_offset += len(api_album_tracks['items'])
            if api_album_tracks['next']: # If there are more pages for this album's songs
                print(f"  Waiting {DELAY_BETWEEN_SONG_PAGES}s before next song page...")
                time.sleep(DELAY_BETWEEN_SONG_PAGES)
            else: # No more pages for this album
                break 
        
        # After processing all songs for an album
        try:
            conn.commit()
            print(f"  Finished processing album '{album_title}'. {album_songs_processed_count} songs checked/processed.")
            print(f"  Added {album_new_songs_added} new songs and {album_new_artists_added} new artists from this album.")
            save_last_processed_album_id(SONG_SYNC_STATE_FILE_PATH, album_db_id)
        except sqlite3.Error as e:
            print(f"Database commit error after album '{album_title}': {e}. State not saved for this album.")
            # This means this album might be reprocessed. Consider rollback or more robust error logging.
            # conn.rollback() # Potentially

        print(f"Waiting {DELAY_BETWEEN_ALBUM_PROCESSING}s before processing next album...")
        time.sleep(DELAY_BETWEEN_ALBUM_PROCESSING)

    conn.close()
    print("\n--- Song Sync Session Complete ---")
    print(f"Total new songs added to DB this session: {total_songs_added_session}")
    print(f"Total new artists (from songs) added to DB this session: {total_artists_added_session}")

if __name__ == "__main__":
    main()
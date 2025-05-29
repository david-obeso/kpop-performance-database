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
# New state file for artist detail enrichment
ARTIST_ENRICH_STATE_FILE_PATH = "spotify_artist_enrich_state.json"
SPOTIPY_REDIRECT_URI = "http://localhost:8888/callback"
# No specific scope needed beyond what basic auth provides for public artist info
API_SCOPE = "user-library-read" # Or even no scope if token already cached and valid

# API call settings
ARTISTS_PER_BATCH = 50  # Max for sp.artists() endpoint
DELAY_BETWEEN_BATCHES = 2 # Seconds to wait between processing batches
RETRY_ATTEMPTS = 5
RETRY_BASE_DELAY = 5  # Seconds

# --- Helper Functions (many are similar to previous scripts) ---
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

def load_last_processed_artist_id(state_file_path):
    if os.path.exists(state_file_path):
        try:
            with open(state_file_path, 'r') as f:
                state = json.load(f)
                return state.get('last_processed_artist_db_id', 0)
        except json.JSONDecodeError:
            print(f"Warning: State file {state_file_path} corrupted. Starting from scratch.")
            return 0
    return 0

def save_last_processed_artist_id(state_file_path, artist_db_id):
    with open(state_file_path, 'w') as f:
        json.dump({'last_processed_artist_db_id': artist_db_id}, f)

def get_db_connection(db_file):
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

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
                raise
        except Exception as e: # Other errors
            print(f"Network or unexpected error: {e}. Retrying in {RETRY_BASE_DELAY * (attempt + 1)}s...")
            time.sleep(RETRY_BASE_DELAY * (attempt + 1))
    print(f"Failed to execute {sp_function.__name__} after {RETRY_ATTEMPTS} retries.")
    return None

# --- Database Interaction ---
def update_artist_details(cursor, spotify_artist_id, details):
    """Updates an artist's details in the database."""
    sql = """
        UPDATE artists
        SET artist_image_url = ?,
            popularity = ?,
            followers_total = ?,
            last_checked_at = ?
        WHERE spotify_artist_id = ?
    """
    try:
        cursor.execute(sql, (
            details['artist_image_url'],
            details['popularity'],
            details['followers_total'],
            details['last_checked_at'],
            spotify_artist_id
        ))
        return cursor.rowcount > 0 # True if update happened
    except sqlite3.Error as e:
        print(f"Error updating artist {spotify_artist_id}: {e}")
        return False

# --- Main Script ---
def main():
    client_id, client_secret = load_credentials(CREDENTIALS_FILE_PATH)
    auth_manager = SpotifyOAuth(client_id=client_id, client_secret=client_secret,
                                redirect_uri=SPOTIPY_REDIRECT_URI, scope=API_SCOPE)
    sp = spotipy.Spotify(auth_manager=auth_manager)

    try:
        user = sp.current_user() # Test authentication
        print(f"Authenticated with Spotify as: {user['display_name']} ({user['id']})")
    except Exception as e:
        print(f"Error during Spotify authentication: {e}")
        exit(1)

    conn = get_db_connection(DB_FILE)
    cursor = conn.cursor()

    last_processed_artist_db_id = load_last_processed_artist_id(ARTIST_ENRICH_STATE_FILE_PATH)
    print(f"Starting artist detail enrichment. Resuming after artist DB ID: {last_processed_artist_db_id}")

    total_artists_updated_session = 0
    current_max_db_id_in_batch = last_processed_artist_db_id

    while True:
        # Fetch a batch of artists from DB that need updating
        # We fetch by artist_id > last_processed_artist_db_id
        cursor.execute("""
            SELECT artist_id, spotify_artist_id, artist_name FROM artists
            WHERE artist_id > ? 
            ORDER BY artist_id ASC
            LIMIT ?
        """, (last_processed_artist_db_id, ARTISTS_PER_BATCH))
        
        db_artists_batch = cursor.fetchall()

        if not db_artists_batch:
            print("No more artists found to enrich. Process complete.")
            break

        spotify_ids_to_fetch = [artist['spotify_artist_id'] for artist in db_artists_batch if artist['spotify_artist_id']]
        
        # Keep track of the DB artist_id for state saving
        if db_artists_batch:
             current_max_db_id_in_batch = db_artists_batch[-1]['artist_id']


        if not spotify_ids_to_fetch:
            print(f"Batch from DB ID {last_processed_artist_db_id + 1} to {current_max_db_id_in_batch} contains no valid Spotify IDs. Skipping.")
            last_processed_artist_db_id = current_max_db_id_in_batch # Advance state past this empty batch
            save_last_processed_artist_id(ARTIST_ENRICH_STATE_FILE_PATH, last_processed_artist_db_id)
            conn.commit() # Commit the state update
            continue

        print(f"\nFetching details for {len(spotify_ids_to_fetch)} artists (DB IDs from {db_artists_batch[0]['artist_id']} to {current_max_db_id_in_batch})...")
        
        api_artists_details = fetch_with_retries(sp.artists, artists=spotify_ids_to_fetch)

        if api_artists_details is None or 'artists' not in api_artists_details:
            print("Failed to fetch artist details for the current batch after retries. Stopping to avoid data loss.")
            # Consider if you want to exit or try to skip this batch.
            # Exiting is safer if the API is consistently failing.
            conn.close()
            exit(1)

        updated_in_batch_count = 0
        for api_artist in api_artists_details['artists']:
            if api_artist is None: # Spotify API returns null for IDs it can't find
                # This could happen if an artist ID was valid once but got removed.
                # Find which spotify_id from our list corresponds to this null
                # For simplicity, we just log it. A more robust solution might mark it in DB.
                print("  Spotify API returned null for one of the requested artist IDs in this batch.")
                continue

            details_to_update = {
                'artist_image_url': api_artist['images'][0]['url'] if api_artist.get('images') else None,
                'popularity': api_artist.get('popularity'),
                'followers_total': api_artist['followers']['total'] if api_artist.get('followers') else None,
                'last_checked_at': get_current_utc_iso_timestamp()
            }

            if update_artist_details(cursor, api_artist['id'], details_to_update):
                # print(f"  Updated details for artist: {api_artist['name']} ({api_artist['id']})")
                updated_in_batch_count +=1
            else:
                print(f"  Failed to update artist {api_artist['name']} ({api_artist['id']}) in DB, though API data was fetched.")
        
        try:
            conn.commit()
            print(f"Committed updates for {updated_in_batch_count} artists in this batch.")
            total_artists_updated_session += updated_in_batch_count
            last_processed_artist_db_id = current_max_db_id_in_batch # Mark this batch as done
            save_last_processed_artist_id(ARTIST_ENRICH_STATE_FILE_PATH, last_processed_artist_db_id)
            print(f"State saved. Last processed artist DB ID: {last_processed_artist_db_id}")
        except sqlite3.Error as e:
            print(f"Database commit error: {e}. State not saved for this batch.")
            conn.rollback() # Rollback changes for this batch if commit failed
            # The script will retry this batch on the next run.

        if len(db_artists_batch) < ARTISTS_PER_BATCH:
            print("Processed the last batch of artists.")
            break # Likely the end

        print(f"Waiting {DELAY_BETWEEN_BATCHES}s before next batch...")
        time.sleep(DELAY_BETWEEN_BATCHES)

    conn.close()
    print("\n--- Artist Enrichment Session Complete ---")
    print(f"Total artists updated with details this session: {total_artists_updated_session}")

if __name__ == "__main__":
    main()
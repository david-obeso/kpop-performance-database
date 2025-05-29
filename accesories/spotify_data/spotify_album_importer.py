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
STATE_FILE_PATH = "spotify_album_sync_state.json" # Stores the last offset
SPOTIPY_REDIRECT_URI = "http://127.0.0.1:8888/callback"
API_SCOPE = "user-library-read"

# API call settings
ITEMS_PER_PAGE = 50  # Max allowed by Spotify for saved albums
DELAY_BETWEEN_PAGES = 2  # Seconds to wait between fetching pages
RETRY_ATTEMPTS = 5
RETRY_BASE_DELAY = 5  # Seconds for base delay in retries

# --- Helper Functions ---
def get_current_utc_iso_timestamp():
    """Returns the current UTC time in ISO 8601 format with Z."""
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')

def load_credentials(file_path):
    """Loads Spotify credentials from the specified file."""
    try:
        with open(file_path, 'r') as f:
            client_id = f.readline().strip()
            client_secret = f.readline().strip()
        if not client_id or not client_secret:
            raise ValueError("Client ID or Secret not found in credentials file.")
        return client_id, client_secret
    except FileNotFoundError:
        print(f"ERROR: Spotify credentials file not found at {file_path}")
        print("Please ensure the file exists and contains your client ID (line 1) and secret (line 2).")
        exit(1)
    except ValueError as ve:
        print(f"ERROR: Reading credentials file: {ve}")
        exit(1)

def load_last_offset(state_file_path):
    """Loads the last successfully processed offset from the state file."""
    if os.path.exists(state_file_path):
        try:
            with open(state_file_path, 'r') as f:
                state = json.load(f)
                return state.get('last_offset', 0)
        except json.JSONDecodeError:
            print(f"Warning: State file {state_file_path} is corrupted. Starting from scratch.")
            return 0
    return 0

def save_last_offset(state_file_path, offset):
    """Saves the current offset to the state file."""
    with open(state_file_path, 'w') as f:
        json.dump({'last_offset': offset}, f)

def get_db_connection(db_file):
    """Establishes and returns a database connection."""
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row # Access columns by name
    # Enable foreign key support if not enabled by default (good practice)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

# --- Database Interaction Functions ---
def get_album_db_id_by_spotify_id(cursor, spotify_album_id):
    """Checks if an album exists by spotify_album_id and returns its DB id."""
    cursor.execute("SELECT album_id FROM albums WHERE spotify_album_id = ?", (spotify_album_id,))
    row = cursor.fetchone()
    return row['album_id'] if row else None

def insert_album(cursor, album_details):
    """Inserts a new album into the database and returns its new album_id."""
    # Ensure all fields from schema are present, using None for optional missing ones
    sql = """
        INSERT INTO albums (
            album_title, spotify_album_id, album_type, total_tracks,
            release_date, release_date_precision, label, popularity,
            cover_image_url, spotify_album_uri, spotify_added_at, last_checked_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    try:
        cursor.execute(sql, (
            album_details['album_title'],
            album_details['spotify_album_id'],
            album_details['album_type'],
            album_details['total_tracks'],
            album_details.get('release_date'), # Can be None
            album_details.get('release_date_precision'), # Can be None
            album_details.get('label'), # Can be None
            album_details.get('popularity'), # Can be None or 0
            album_details.get('cover_image_url'), # Can be None
            album_details['spotify_album_uri'],
            album_details['spotify_added_at'],
            album_details['last_checked_at']
        ))
        return cursor.lastrowid
    except sqlite3.IntegrityError as e:
        print(f"Error inserting album {album_details['spotify_album_id']}: {e}")
        # This might happen if spotify_album_id UNIQUE constraint is violated,
        # though get_album_db_id_by_spotify_id should prevent this.
        # Or other NOT NULL constraints if data is bad.
        return None


def get_artist_db_id_by_spotify_id(cursor, spotify_artist_id):
    """Checks if an artist exists by spotify_artist_id and returns its DB id."""
    cursor.execute("SELECT artist_id FROM artists WHERE spotify_artist_id = ?", (spotify_artist_id,))
    row = cursor.fetchone()
    return row['artist_id'] if row else None

def insert_artist(cursor, artist_details):
    """Inserts a new artist into the database and returns its new artist_id."""
    sql = """
        INSERT INTO artists (
            artist_name, spotify_artist_id, spotify_artist_uri, last_checked_at
            -- artist_image_url, popularity, followers_total are intentionally omitted (will be NULL)
        ) VALUES (?, ?, ?, ?)
    """
    try:
        current_time = get_current_utc_iso_timestamp()
        cursor.execute(sql, (
            artist_details['artist_name'],
            artist_details['spotify_artist_id'],
            artist_details['spotify_artist_uri'],
            current_time # last_checked_at for the new artist
        ))
        return cursor.lastrowid
    except sqlite3.IntegrityError as e:
        # This could be due to UNIQUE constraint on spotify_artist_id (should be caught by get_artist_db_id)
        # or on artist_name if a different artist_id has the same name.
        print(f"Error inserting artist {artist_details['spotify_artist_id']} ({artist_details['artist_name']}): {e}")
        # If it failed due to name conflict, try to fetch by spotify_artist_id again,
        # in case it was inserted by a race condition (highly unlikely in single-thread script)
        # or if the logic needs refinement for name conflicts.
        # For now, we let the caller handle this (e.g., by re-fetching ID).
        return None


def insert_album_artist_link(cursor, album_db_id, artist_db_id, artist_order):
    """Inserts a link between an album and an artist."""
    sql = """
        INSERT OR IGNORE INTO album_artist_link_simplified (
            album_id, artist_id, artist_order
        ) VALUES (?, ?, ?)
    """
    # INSERT OR IGNORE is used because the PK is (album_id, artist_id).
    # If we process an album only once, this link shouldn't exist yet.
    try:
        cursor.execute(sql, (album_db_id, artist_db_id, artist_order))
    except sqlite3.IntegrityError as e:
        print(f"Error inserting album-artist link for album_id {album_db_id}, artist_id {artist_db_id}: {e}")


# --- Main Script ---
def main():
    client_id, client_secret = load_credentials(CREDENTIALS_FILE_PATH)

    # Initialize Spotipy with OAuth
    # The .cache file will be created by default in the script's directory.
    # You might want to specify cache_path in SpotifyOAuth if you prefer another location.
    auth_manager = SpotifyOAuth(client_id=client_id,
                                client_secret=client_secret,
                                redirect_uri=SPOTIPY_REDIRECT_URI,
                                scope=API_SCOPE)
    sp = spotipy.Spotify(auth_manager=auth_manager)

    try:
        # Test authentication
        user = sp.current_user()
        print(f"Successfully authenticated with Spotify as: {user['display_name']} ({user['id']})")
    except spotipy.SpotifyException as e:
        print(f"Spotify API authentication/authorization error: {e}")
        print("Ensure you have authorized the application when prompted by your browser.")
        exit(1)
    except Exception as e: # Catch other potential errors like network issues during auth
        print(f"Error during Spotify authentication: {e}")
        exit(1)

    conn = get_db_connection(DB_FILE)
    cursor = conn.cursor()

    current_offset = load_last_offset(STATE_FILE_PATH)
    print(f"Starting album sync. Resuming from offset: {current_offset}")

    total_albums_processed_this_session = 0
    total_new_albums_added = 0
    total_new_artists_added = 0

    while True:
        print(f"Fetching saved albums page: offset={current_offset}, limit={ITEMS_PER_PAGE}")
        results = None
        for attempt in range(RETRY_ATTEMPTS):
            try:
                results = sp.current_user_saved_albums(limit=ITEMS_PER_PAGE, offset=current_offset)
                break # Success
            except spotipy.SpotifyException as e:
                if e.http_status == 429: # Rate limit
                    retry_after = e.headers.get('Retry-After', RETRY_BASE_DELAY * (attempt + 1))
                    print(f"Rate limited. Retrying after {retry_after} seconds...")
                    time.sleep(int(retry_after) + 1) # Add 1s buffer
                elif e.http_status >= 500: # Server error
                    print(f"Spotify server error ({e.http_status}). Retrying in {RETRY_BASE_DELAY * (attempt + 1)}s...")
                    time.sleep(RETRY_BASE_DELAY * (attempt + 1))
                else:
                    print(f"Spotify API error: {e}")
                    conn.close()
                    exit(1) # Unrecoverable API error for now
            except Exception as e: # Other errors like requests.exceptions.ConnectionError
                print(f"Network or unexpected error: {e}. Retrying in {RETRY_BASE_DELAY * (attempt + 1)}s...")
                time.sleep(RETRY_BASE_DELAY * (attempt + 1))
        
        if results is None:
            print("Failed to fetch albums after multiple retries. Exiting.")
            conn.close()
            exit(1)

        if not results['items']:
            print("No more albums found. Sync complete.")
            break

        page_albums_added = 0
        page_artists_added = 0

        for item in results['items']:
            api_album = item['album']
            spotify_added_at_ts = item['added_at'] # This is when user added album to library

            # Prepare album data for insertion
            album_data_to_insert = {
                'album_title': api_album['name'],
                'spotify_album_id': api_album['id'],
                'album_type': api_album['album_type'],
                'total_tracks': api_album['total_tracks'],
                'release_date': api_album.get('release_date'),
                'release_date_precision': api_album.get('release_date_precision'),
                'label': api_album.get('label'),
                'popularity': api_album.get('popularity', 0), # API can omit, default to 0
                'cover_image_url': api_album['images'][0]['url'] if api_album.get('images') else None,
                'spotify_album_uri': api_album['uri'],
                'spotify_added_at': spotify_added_at_ts,
                'last_checked_at': get_current_utc_iso_timestamp()
            }
            
            album_db_id = get_album_db_id_by_spotify_id(cursor, album_data_to_insert['spotify_album_id'])

            if album_db_id:
                print(f"Album '{album_data_to_insert['album_title']}' ({album_data_to_insert['spotify_album_id']}) already exists in DB (ID: {album_db_id}). Skipping.")
                # Optionally, you could update 'last_checked_at' or other fields here if desired.
            else:
                album_db_id = insert_album(cursor, album_data_to_insert)
                if album_db_id:
                    print(f"Added album '{album_data_to_insert['album_title']}' ({album_data_to_insert['spotify_album_id']}) to DB (New ID: {album_db_id}).")
                    total_new_albums_added += 1
                    page_albums_added +=1

                    # Process artists for this new album
                    for order_idx, api_artist_summary in enumerate(api_album['artists']):
                        artist_order = order_idx + 1
                        artist_spotify_id = api_artist_summary['id']
                        
                        artist_db_id = get_artist_db_id_by_spotify_id(cursor, artist_spotify_id)
                        
                        if not artist_db_id:
                            artist_data_to_insert = {
                                'artist_name': api_artist_summary['name'],
                                'spotify_artist_id': artist_spotify_id,
                                'spotify_artist_uri': api_artist_summary['uri']
                                # last_checked_at will be set by insert_artist
                            }
                            artist_db_id = insert_artist(cursor, artist_data_to_insert)
                            if artist_db_id:
                                print(f"  Added artist '{artist_data_to_insert['artist_name']}' ({artist_spotify_id}) to DB (New ID: {artist_db_id}).")
                                total_new_artists_added += 1
                                page_artists_added +=1
                            else:
                                # If artist insertion failed, try to fetch ID again in case of name conflict + existing spotify_id
                                print(f"  Failed to insert artist '{api_artist_summary['name']}' ({artist_spotify_id}). Attempting to find existing by Spotify ID.")
                                artist_db_id = get_artist_db_id_by_spotify_id(cursor, artist_spotify_id)
                                if not artist_db_id:
                                     print(f"  Could not resolve artist '{api_artist_summary['name']}' ({artist_spotify_id}) after insertion failure. Skipping link.")
                                     continue # Skip linking this artist
                                else:
                                     print(f"  Found existing artist '{api_artist_summary['name']}' ({artist_spotify_id}) with DB ID: {artist_db_id} after initial insert issue.")
                        
                        if artist_db_id and album_db_id: # Ensure both IDs are valid
                            insert_album_artist_link(cursor, album_db_id, artist_db_id, artist_order)
                            # print(f"    Linked album ID {album_db_id} to artist ID {artist_db_id} (Order: {artist_order}).")
                else:
                    print(f"Failed to insert album '{album_data_to_insert['album_title']}' into DB. Skipping its artists.")
            total_albums_processed_this_session +=1

        # Commit changes after processing the current page
        try:
            conn.commit()
            print(f"Committed {page_albums_added} new albums and {page_artists_added} new artists from this page.")
        except sqlite3.Error as e:
            print(f"Database commit error: {e}. Some data for this page might not be saved.")
            # Decide if to rollback or try to proceed carefully.
            # For simplicity here, we log and continue. A more robust solution might try to rollback.
            # conn.rollback() # Potentially

        current_offset += len(results['items'])
        save_last_offset(STATE_FILE_PATH, current_offset)
        print(f"Progress: Processed {total_albums_processed_this_session} albums this session. Next offset: {current_offset}")
        print(f"Total new albums added this session: {total_new_albums_added}")
        print(f"Total new artists added this session: {total_new_artists_added}")

        # Be a good API citizen
        print(f"Waiting for {DELAY_BETWEEN_PAGES} seconds before next API call...")
        time.sleep(DELAY_BETWEEN_PAGES)

    conn.close()
    print("Database connection closed.")
    print(f"--- Sync Session Summary ---")
    print(f"Total albums processed (checked/added): {total_albums_processed_this_session}")
    print(f"Total new albums inserted into DB: {total_new_albums_added}")
    print(f"Total new artists inserted into DB: {total_new_artists_added}")

if __name__ == "__main__":
    main()
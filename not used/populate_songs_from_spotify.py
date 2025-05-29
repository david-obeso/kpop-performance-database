import sqlite3
import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import time
import re # For flexible genre matching

# --- Database Configuration ---
DATABASE_FILE = "kpop_database.db"

# --- Spotify API Setup ---
CREDENTIALS_FILE_PATH = os.path.expanduser("~/.spotify_credentials")

try:
    with open(CREDENTIALS_FILE_PATH, 'r') as f:
        spotify_client_id = f.readline().strip()
        spotify_client_secret = f.readline().strip()
    if not spotify_client_id or not spotify_client_secret:
        raise ValueError("Client ID or Secret not found in credentials file.")
    auth_manager = SpotifyClientCredentials(client_id=spotify_client_id, client_secret=spotify_client_secret)
    sp = spotipy.Spotify(auth_manager=auth_manager)
    print("Successfully authenticated with Spotify API using credentials from file.")
except FileNotFoundError:
    print(f"ERROR: Spotify credentials file not found at {CREDENTIALS_FILE_PATH}")
    print("Please ensure the file exists and contains your client ID and secret on separate lines.")
    print("Alternatively, set SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET environment variables.")
    exit()
except ValueError as ve:
    print(f"ERROR: Reading credentials file: {ve}")
    exit()
except Exception as e:
    print(f"Error authenticating with Spotify: {e}")
    exit()

# --- Database Functions ---
def create_connection(db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
    return conn

def create_table(conn, create_table_sql):
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except sqlite3.Error as e:
        print(f"Error creating table: {e}")

SQL_CREATE_SONG_ARTISTS_TABLE = """CREATE TABLE IF NOT EXISTS song_artists (
                                    song_id INTEGER NOT NULL,
                                    group_id INTEGER NOT NULL,
                                    FOREIGN KEY (song_id) REFERENCES songs (song_id),
                                    FOREIGN KEY (group_id) REFERENCES groups (group_id),
                                    PRIMARY KEY (song_id, group_id)
                                );"""

def ensure_spotify_id_column_exists(conn):
    """Checks if spotify_artist_id column exists in groups table, adds if not."""
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(groups);")
        columns = [info[1] for info in cursor.fetchall()]
        if 'spotify_artist_id' not in columns:
            print("Adding 'spotify_artist_id' column to 'groups' table...")
            cursor.execute("ALTER TABLE groups ADD COLUMN spotify_artist_id TEXT;")
            conn.commit()
            print("'spotify_artist_id' column added.")
    except sqlite3.Error as e:
        print(f"Error checking/adding 'spotify_artist_id' column: {e}")

# --- Main Logic ---
def fetch_and_populate_songs():
    conn = create_connection(DATABASE_FILE)
    if not conn:
        return

    ensure_spotify_id_column_exists(conn)
    create_table(conn, SQL_CREATE_SONG_ARTISTS_TABLE)
    cursor = conn.cursor()

    cursor.execute("SELECT group_id, group_name, spotify_artist_id FROM groups")
    groups_data = cursor.fetchall()
    print(f"Found {len(groups_data)} groups in the database.")

    total_songs_added = 0
    total_links_added = 0
    skipped_groups_count = 0
    already_processed_with_id = 0
    groups_updated_with_new_id = 0


    KPOP_GENRE_KEYWORDS = [
        "k-pop", "kpop", "korean pop", "k-pop boy group", "k-pop girl group",
        "korean r&b", "k-rap", "korean hip hop", "korean idol", "j-pop", "c-pop", "asian pop"
    ] # Added j-pop, c-pop as related

    for group_id, group_name, existing_spotify_id in groups_data:
        print(f"\n--------------------------------------------------")
        print(f"Processing Your Group: {group_name} (ID: {group_id})")
        print(f"--------------------------------------------------")

        chosen_spotify_artist = None
        spotify_artist_id_to_use = None

        if existing_spotify_id:
            print(f"  This group already has a stored Spotify Artist ID: {existing_spotify_id}")
            try:
                artist_details = sp.artist(existing_spotify_id)
                print(f"  Stored ID points to: {artist_details['name']}")
                while True:
                    action = input(f"  Use this stored ID? (y/n/c - yes/no to re-search/change ID): ").lower()
                    if action == 'y':
                        spotify_artist_id_to_use = existing_spotify_id
                        chosen_spotify_artist = artist_details
                        print(f"  Proceeding with stored Spotify ID: {spotify_artist_id_to_use} ({chosen_spotify_artist['name']})")
                        already_processed_with_id += 1
                        break
                    elif action == 'n':
                        print("  Okay, will re-search for this group.")
                        existing_spotify_id = None
                        break
                    elif action == 'c':
                        new_id = input("  Enter new Spotify Artist ID (or leave blank to search): ").strip()
                        if new_id:
                            try:
                                artist_details_new = sp.artist(new_id)
                                print(f"  New ID points to: {artist_details_new['name']}")
                                confirm_new = input(f"  Use this new ID '{new_id}' ({artist_details_new['name']})? (y/n): ").lower()
                                if confirm_new == 'y':
                                    spotify_artist_id_to_use = new_id
                                    chosen_spotify_artist = artist_details_new
                                    cursor.execute("UPDATE groups SET spotify_artist_id = ? WHERE group_id = ?", (spotify_artist_id_to_use, group_id))
                                    conn.commit()
                                    print(f"  Group '{group_name}' updated with new Spotify ID: {spotify_artist_id_to_use}")
                                    groups_updated_with_new_id +=1
                                    break
                                else:
                                    print("  New ID not confirmed. Will proceed to search.")
                                    existing_spotify_id = None; break
                            except Exception as e_new_id:
                                print(f"  Error validating new Spotify ID '{new_id}': {e_new_id}. Will proceed to search.")
                                existing_spotify_id = None; break
                        else:
                            existing_spotify_id = None; break
                    else:
                        print("  Invalid input. Please enter 'y', 'n', or 'c'.")
            except Exception as e_stored_id:
                print(f"  Error verifying stored Spotify ID '{existing_spotify_id}': {e_stored_id}")
                print("  Proceeding to search for this group.")
                existing_spotify_id = None

        if not spotify_artist_id_to_use:
            try:
                query = f'artist:{group_name}'
                results = sp.search(q=query, type='artist', limit=15)
                spotify_artists_found_raw = results['artists']['items']

                if not spotify_artists_found_raw:
                    print(f"  Could not find any artist matching '{group_name}' (query: '{query}') on Spotify. Skipping.")
                    skipped_groups_count += 1
                    continue

                group_name_lower = group_name.lower()
                def get_artist_score(artist_item_tuple): # Receives (index, artist_item)
                    original_index, artist_item = artist_item_tuple
                    score = 0
                    artist_name_lower = artist_item['name'].lower()
                    
                    if group_name_lower == artist_name_lower or \
                       (f" {group_name_lower} " in f" {artist_name_lower} ") or \
                       (artist_name_lower.startswith(group_name_lower + " (")) or \
                       (artist_name_lower.startswith(group_name_lower + " [")):
                        score += 100

                    artist_genres = [g.lower() for g in artist_item.get('genres', [])]
                    has_kpop_genre = False
                    for keyword in KPOP_GENRE_KEYWORDS:
                        for genre in artist_genres:
                            if keyword in genre:
                                score += 50
                                has_kpop_genre = True; break
                        if has_kpop_genre: break
                    
                    if has_kpop_genre: score += artist_item.get('popularity', 0) / 5

                    if score < 100:
                        non_kpop_indicators = ["classical", "orchestra", "symphony", "choir", "opera", "conductor"]
                        for indicator in non_kpop_indicators:
                            if any(indicator in genre for genre in artist_genres):
                                score -= 200; break
                    
                    # Add a small penalty for being further down Spotify's original list to act as a tie-breaker
                    score -= original_index * 0.1 
                    return score

                spotify_artists_sorted_with_indices = sorted(enumerate(spotify_artists_found_raw), key=get_artist_score, reverse=True)
                spotify_artists_sorted = [artist for index, artist in spotify_artists_sorted_with_indices] # Get back just artist items
                
                spotify_artists_found = spotify_artists_sorted[:7]

                if not spotify_artists_found:
                    print(f"  No suitable artist candidates after filtering for '{group_name}'. Skipping.")
                    skipped_groups_count += 1
                    continue

                chosen_spotify_artist = None
                if len(spotify_artists_found) == 1:
                    artist_candidate = spotify_artists_found[0]
                    print(f"\nFound 1 Spotify artist candidate for '{group_name}':")
                    print(f"  Name: {artist_candidate['name']}")
                    print(f"  Genres: {', '.join(artist_candidate.get('genres', [])) if artist_candidate.get('genres') else 'N/A'}")
                    print(f"  Popularity: {artist_candidate.get('popularity', 'N/A')}")
                    print(f"  Followers: {artist_candidate.get('followers', {}).get('total', 'N/A')}")
                    try:
                        sample_albums = sp.artist_albums(artist_candidate['id'], album_type='album,single', limit=1)
                        if sample_albums and sample_albums['items']:
                            sample_tracks_result = sp.album_tracks(sample_albums['items'][0]['id'], limit=3)
                            if sample_tracks_result and sample_tracks_result['items']:
                                print("  Sample Tracks:")
                                for i, track_item in enumerate(sample_tracks_result['items']):
                                    print(f"    {i+1}. {track_item['name']}")
                    except Exception as sample_e: print(f"  (Could not fetch sample tracks: {sample_e})")
                    
                    while True:
                        choice = input(f"  Proceed with this artist for '{group_name}'? (y/n/s): ").lower()
                        if choice == 'y': chosen_spotify_artist = artist_candidate; break
                        elif choice in ['n', 's']: skipped_groups_count += 1; break
                        else: print("  Invalid input. Please enter 'y', 'n', or 's'.")
                    if not chosen_spotify_artist: continue
                else:
                    print(f"\nFound multiple Spotify artist candidates for '{group_name}':")
                    for i, artist_item in enumerate(spotify_artists_found):
                        print(f"  {i+1}. Name: {artist_item['name']}")
                        print(f"     Genres: {', '.join(artist_item.get('genres', [])) if artist_item.get('genres') else 'N/A'}")
                        print(f"     Popularity: {artist_item.get('popularity', 'N/A')}")
                        print(f"     Followers: {artist_item.get('followers', {}).get('total', 'N/A')}")
                        try:
                            sample_albums = sp.artist_albums(artist_item['id'], album_type='album,single', limit=1)
                            if sample_albums and sample_albums['items']:
                                sample_tracks_result = sp.album_tracks(sample_albums['items'][0]['id'], limit=2)
                                if sample_tracks_result and sample_tracks_result['items']:
                                    print("     Sample Tracks:")
                                    for t_idx, track_item in enumerate(sample_tracks_result['items']): print(f"       - {track_item['name']}")
                        except Exception as sample_e: print(f"     (Could not fetch sample tracks: {sample_e})")
                        print("-" * 20)
                    
                    while True:
                        try:
                            selection = input(f"  Enter num (1-{len(spotify_artists_found)}) or 's' to skip: ").lower()
                            if selection == 's': skipped_groups_count += 1; break
                            artist_index = int(selection) - 1
                            if 0 <= artist_index < len(spotify_artists_found):
                                chosen_spotify_artist = spotify_artists_found[artist_index]; break
                            else: print(f"  Invalid number.")
                        except ValueError: print(f"  Invalid input.")
                    if not chosen_spotify_artist: continue
                
                if chosen_spotify_artist:
                    spotify_artist_id_to_use = chosen_spotify_artist['id']
                    try:
                        cursor.execute("UPDATE groups SET spotify_artist_id = ? WHERE group_id = ?", (spotify_artist_id_to_use, group_id))
                        conn.commit()
                        print(f"  Group '{group_name}' linked with Spotify ID: {spotify_artist_id_to_use} ({chosen_spotify_artist['name']})")
                        groups_updated_with_new_id += 1
                    except sqlite3.Error as e_update:
                        print(f"  ERROR updating group with Spotify ID: {e_update}")
            
            except spotipy.exceptions.SpotifyException as e:
                print(f"  Spotify API error during search for group '{group_name}': {e}")
                if e.http_status == 429:
                    retry_after = int(e.headers.get('Retry-After', 60)); print(f"  RATELIMIT: Waiting for {retry_after} seconds..."); time.sleep(retry_after + 5)
                skipped_groups_count += 1; continue
            except Exception as e_search:
                print(f"  An unexpected error occurred during search for group '{group_name}': {e_search}")
                skipped_groups_count += 1; continue
        
        if not spotify_artist_id_to_use:
            if not chosen_spotify_artist and not existing_spotify_id: # Avoid double counting if already skipped
                 print(f"  No Spotify artist ID to use for '{group_name}'. Skipping song fetching.") # Should be rare now
                 # skipped_groups_count +=1 # This might double count if already counted in search fail
            continue
        
        # Ensure chosen_spotify_artist is populated for display name if using an ID
        if not chosen_spotify_artist and spotify_artist_id_to_use: # Should only happen if manually changed and details not re-fetched
            try: chosen_spotify_artist = sp.artist(spotify_artist_id_to_use)
            except: chosen_spotify_artist = {'name': 'Artist ID ' + spotify_artist_id_to_use} # Fallback display


        print(f"\n  Fetching songs for: {chosen_spotify_artist.get('name', spotify_artist_id_to_use)} using ID: {spotify_artist_id_to_use}")
        albums_fetched_count = 0
        songs_for_this_group = 0
        for album_type in ['album', 'single']:
            offset = 0; limit = 50
            while True:
                try:
                    artist_albums = sp.artist_albums(spotify_artist_id_to_use, album_type=album_type, limit=limit, offset=offset, country='KR')
                except spotipy.exceptions.SpotifyException as e:
                    if e.http_status == 429: retry_after = int(e.headers.get('Retry-After', 60)); print(f"  Rate limited. Waiting for {retry_after} sec..."); time.sleep(retry_after + 5); continue
                    else: print(f"  Spotify API error fetching albums: {e}"); break 
                except Exception as e_albums: print(f"  Unexpected error fetching albums: {e_albums}"); break
                if not artist_albums or not artist_albums['items']: break
                for album in artist_albums['items']:
                    album_main_artists_ids = [art['id'] for art in album.get('artists', [])]
                    if spotify_artist_id_to_use not in album_main_artists_ids: continue
                    albums_fetched_count += 1
                    track_offset = 0; track_limit = 50
                    while True:
                        try:
                            album_tracks = sp.album_tracks(album['id'], limit=track_limit, offset=track_offset, market='KR')
                        except spotipy.exceptions.SpotifyException as e:
                            if e.http_status == 429: retry_after = int(e.headers.get('Retry-After', 60)); print(f"  Rate limited (tracks). Waiting for {retry_after} sec..."); time.sleep(retry_after + 5); continue
                            else: print(f"  Spotify API error fetching tracks: {e}"); break 
                        except Exception as e_tracks: print(f"  Unexpected error fetching tracks: {e_tracks}"); break
                        if not album_tracks or not album_tracks['items']: break
                        for track in album_tracks['items']:
                            song_title = track['name']
                            track_artist_ids = [artist['id'] for artist in track['artists']]
                            if spotify_artist_id_to_use not in track_artist_ids: continue
                            try:
                                cursor.execute("INSERT OR IGNORE INTO songs (song_title) VALUES (?)", (song_title,))
                                if cursor.rowcount > 0: total_songs_added += 1
                                cursor.execute("SELECT song_id FROM songs WHERE song_title = ?", (song_title,))
                                song_id_result = cursor.fetchone()
                                if song_id_result:
                                    song_id = song_id_result[0]
                                    cursor.execute("INSERT OR IGNORE INTO song_artists (song_id, group_id) VALUES (?, ?)", (song_id, group_id))
                                    if cursor.rowcount > 0: songs_for_this_group +=1; total_links_added += 1
                                else: print(f"      ERROR: Could not get song_id for {song_title} after insert/ignore.")
                            except sqlite3.Error as db_err: print(f"      Database error for song '{song_title}': {db_err}")
                        track_offset += len(album_tracks['items'])
                        if not album_tracks['next']: break
                        time.sleep(0.1) # Be nice to API
                offset += len(artist_albums['items'])
                if not artist_albums['next']: break
                time.sleep(0.2) # Be nice to API
        print(f"  Fetched details for {albums_fetched_count} albums/singles and added/linked {songs_for_this_group} songs for {chosen_spotify_artist.get('name', spotify_artist_id_to_use)}.")
        conn.commit()

    print(f"\n--- Summary ---")
    print(f"Total new songs added to 'songs' table: {total_songs_added}")
    print(f"Total new links added to 'song_artists' table: {total_links_added}")
    print(f"Groups processed using a previously stored Spotify ID: {already_processed_with_id}")
    print(f"Groups newly linked or updated with a Spotify ID this run: {groups_updated_with_new_id}")
    print(f"Total groups skipped by user or not found this run: {skipped_groups_count}")

    if conn:
        conn.close()
    print("\nFinished populating songs from Spotify.")

if __name__ == "__main__":
    fetch_and_populate_songs()
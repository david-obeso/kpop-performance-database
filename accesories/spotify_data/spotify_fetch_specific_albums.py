import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
import time

# --- Configuration ---
# CREDENTIALS_FILE_PATH should be a plain text file:
# Line 1: SPOTIPY_CLIENT_ID
# Line 2: SPOTIPY_CLIENT_SECRET
CREDENTIALS_FILE_PATH = os.path.expanduser("~/.spotify_credentials")
SPOTIPY_REDIRECT_URI = "http://127.0.0.1:8888/callback"
# Scope might not be strictly necessary for public data, but SpotipyOAuth usually requires one.
# 'user-library-read' is fine, or you could use a more minimal one if preferred.
API_SCOPE = "user-library-read"

ALBUM_IDS_TO_FETCH = [
    "6Jckat6ByGCQr0HyFQLf0r",
    "7n5dBQtpZrf4jyeFUwYRBI",
    "6k40GkN3d0Rjl7C4luPbCR"
]

# --- API Call Delays (seconds) ---
DELAY_PER_ALBUM_FETCH = 1  # Delay after fetching an album's details
DELAY_PER_ARTIST_FETCH = 1 # Delay after fetching artist details

# --- Helper Functions (reused from previous script) ---
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
            cache_path=".spotifycache_album_info_script" # Use a different cache file
        )
        sp = spotipy.Spotify(auth_manager=auth_manager)
        sp.me() # Test authentication
        print("Successfully authenticated with Spotify.")
        return sp
    except Exception as e:
        print(f"Spotify authentication failed: {e}")
        return None

# --- Main Logic ---
def main():
    print("Starting script to fetch album and artist info...")
    client_id, client_secret = load_credentials()
    if not client_id or not client_secret:
        print("Exiting due to missing credentials.")
        return

    sp = get_spotify_client(client_id, client_secret)
    if not sp:
        print("Exiting due to Spotify authentication failure.")
        return

    print(f"\nFetching information for {len(ALBUM_IDS_TO_FETCH)} album(s)...\n")

    for album_id in ALBUM_IDS_TO_FETCH:
        print(f"--- Processing Album ID: {album_id} ---")
        try:
            print(f"Fetching album details for {album_id}...")
            album_data = sp.album(album_id)
            time.sleep(DELAY_PER_ALBUM_FETCH)

            if not album_data:
                print(f"Could not retrieve data for album ID: {album_id}\n")
                continue

            print(f"\nAlbum: {album_data.get('name', 'N/A')}")
            print(f"  ID: {album_data.get('id', 'N/A')}")
            print(f"  Type: {album_data.get('album_type', 'N/A')}")
            print(f"  Release Date: {album_data.get('release_date', 'N/A')} (Precision: {album_data.get('release_date_precision', 'N/A')})")
            print(f"  Total Tracks: {album_data.get('total_tracks', 'N/A')}")
            print(f"  Popularity: {album_data.get('popularity', 'N/A')}")
            print(f"  Label: {album_data.get('label', 'N/A')}")
            if album_data.get('images'):
                print(f"  Cover Art URL: {album_data['images'][0]['url']}")
            print(f"  Spotify URI: {album_data.get('uri', 'N/A')}")

            album_artist_ids = []
            if album_data.get('artists'):
                for artist_summary in album_data['artists']:
                    if artist_summary.get('id'):
                        album_artist_ids.append(artist_summary['id'])
            
            if album_artist_ids:
                print("\n  Artists on this Album:")
                print(f"  Fetching details for {len(album_artist_ids)} artist(s)...")
                # Fetch full artist details (can be batched if many, but for typical album artists, it's few)
                # Using sp.artists for batching even if it's just one artist.
                artist_details_list = sp.artists(artists=album_artist_ids)
                time.sleep(DELAY_PER_ARTIST_FETCH)

                if artist_details_list and artist_details_list.get('artists'):
                    for artist_full_data in artist_details_list['artists']:
                        if artist_full_data: # API can return None for some IDs
                            print(f"    - Artist: {artist_full_data.get('name', 'N/A')}")
                            print(f"        ID: {artist_full_data.get('id', 'N/A')}")
                            print(f"        Popularity: {artist_full_data.get('popularity', 'N/A')}")
                            followers_data = artist_full_data.get('followers')
                            followers_total = followers_data.get('total', 'N/A') if followers_data else 'N/A'
                            print(f"        Followers: {followers_total}")
                            if artist_full_data.get('images'):
                                print(f"        Image URL: {artist_full_data['images'][0]['url']}")
                            print(f"        Genres: {', '.join(artist_full_data.get('genres', [])) if artist_full_data.get('genres') else 'N/A'}")
                            print(f"        Spotify URI: {artist_full_data.get('uri', 'N/A')}")
                        else:
                            print("    - Could not retrieve full details for one of the artists.")
                else:
                    print("    - Could not retrieve artist details.")
            else:
                print("  No primary artists listed for this album directly (check track artists if needed).")

        except spotipy.SpotifyException as e:
            print(f"Spotify API error for album {album_id}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred while processing album {album_id}: {e}")
        
        print("\n------------------------------------\n")

    print("Script finished.")

if __name__ == "__main__":
    main()
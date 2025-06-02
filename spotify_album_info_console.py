import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
import sys
import time

# --- Configuration ---
CREDENTIALS_FILE_PATH = os.path.expanduser("~/.spotify_credentials")
SPOTIPY_REDIRECT_URI = "http://127.0.0.1:8888/callback"
API_SCOPE = "user-library-read"

# --- Helper Functions ---
def load_credentials():
    if not os.path.exists(CREDENTIALS_FILE_PATH):
        print(f"Error: Credentials file not found at {CREDENTIALS_FILE_PATH}")
        sys.exit(1)
    with open(CREDENTIALS_FILE_PATH, 'r') as f:
        lines = f.readlines()
        if len(lines) < 2:
            print(f"Error: Credentials file {CREDENTIALS_FILE_PATH} is not formatted correctly.")
            sys.exit(1)
        client_id = lines[0].strip()
        client_secret = lines[1].strip()
        return client_id, client_secret

def get_spotify_client(client_id, client_secret):
    auth_manager = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=SPOTIPY_REDIRECT_URI,
        scope=API_SCOPE,
        cache_path=".spotifycache_console_album_query"
    )
    sp = spotipy.Spotify(auth_manager=auth_manager)
    return sp

def fetch_with_retries(sp_function, *args, **kwargs):
    RETRY_ATTEMPTS = 5
    RETRY_BASE_DELAY = 5
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

def main():
    client_id, client_secret = load_credentials()
    sp = get_spotify_client(client_id, client_secret)
    artist_name = input("Enter the artist name to search for: ").strip()
    if not artist_name:
        print("No artist name entered. Exiting.")
        return
    print(f"Searching for artist: {artist_name} ...")
    artist_results = fetch_with_retries(sp.search, q=f"artist:{artist_name}", type="artist", limit=5)
    if not artist_results or not artist_results['artists']['items']:
        print(f"Artist '{artist_name}' not found.")
        return
    artist = None
    for a in artist_results['artists']['items']:
        if a['name'].lower() == artist_name.lower():
            artist = a
            break
    if not artist:
        print(f"Artist '{artist_name}' not found in search results.")
        return
    print(f"Found artist: {artist['name']} (Spotify ID: {artist['id']})")
    print(f"Followers: {artist.get('followers', {}).get('total', 'N/A')}")
    print(f"Popularity: {artist.get('popularity', 'N/A')}")
    print(f"Genres: {', '.join(artist.get('genres', [])) or 'N/A'}")
    print(f"Spotify URL: {artist.get('external_urls', {}).get('spotify', 'N/A')}")
    if artist.get('images'):
        print(f"Image URL: {artist['images'][0]['url']}")
    else:
        print("Image URL: N/A")

    # Fetch and print albums
    print("\nAlbums:")
    albums = []
    offset = 0
    while True:
        album_results = fetch_with_retries(sp.artist_albums, artist['id'], album_type='album', limit=50, offset=offset)
        if not album_results or not album_results['items']:
            break
        albums.extend(album_results['items'])
        if not album_results.get('next'):
            break
        offset += len(album_results['items'])
    if not albums:
        print("  No albums found.")
    else:
        seen = set()
        for idx, album in enumerate(albums, 1):
            # Avoid duplicates (Spotify API can return duplicates for different markets)
            if album['id'] in seen:
                continue
            seen.add(album['id'])
            print(f"  {idx}. {album['name']} (Release: {album.get('release_date', 'N/A')}, Tracks: {album.get('total_tracks', 'N/A')})")

if __name__ == "__main__":
    main()

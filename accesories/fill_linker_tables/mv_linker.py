import sqlite3
import os
import re
from datetime import datetime, timezone

# --- Configuration ---
NEW_DB_PATH = 'KpopDatabase_new.db'

# --- Normalization Fluff & Function (Refined from previous discussion) ---
LITERAL_FLUFF_TERMS = [
    # Specific phrases first (longer ones, or those with special chars that re.escape will handle)
    "| 1thekillpo", "| mnet", "| studio choom original", "| studio choom",
    "| stone performance", "| dance society | performance", "| on the spot",
    "| visual track", "[m2 exclusive]", "[move to performance]",
    "| performance | off the stage", "[mmt stage]",
    "(dingo music @stage)", "(repetida)", "(uhd 2160p hevc10 pcm)",
    "(danielle&haerin ver.)", "(hanni ver.)",
    "(performance flower moving ver)", "[masterpiece]", "(human eye ver.)",
    "[performance37]", "(dance performance issue club)",
    "(pole dance performance video)",
    "(japanese ver.)", "(remix ver.)", "(dance ver.)",
    "(choreography version)", "(performance ver.)", "(korean ver.)",
    "(japanese dance ver.)", "(original ver.)", "(chinese_ver.)",
    "(dance video)", "(choreography ver.)", "(choreography b ver.)",
    "(special choreography)", "(jap. ver.)", "(performance video)", 
    "(demicat remix)", "(choreography video)", "(english ver.)",
    "(performance stage)", "(school ver.)", "(live performance)",
    "special clip performance ver.", "band live",
    "special stage performance",
    "- i'll (show) it", 
    "- choreography ver",
    "mv", "music video", "official video", "official mv",
    "perf. video", "lyric video", "special video", "live clip", "self cam",
    "(official)", "(performance)", "(live)", "(acoustic)",
    "ver.", "version", "ver", 
    "dance practice",
    "teaser", "trailer",
    "안무영상", "뮤직비디오"
]
REGEX_PATTERNS_POST_FLUFF = [
    re.compile(r'\s*\([^)]*\)\s*'),
    re.compile(r'\s*\[[^\]]*\]\s*')
]

def normalize_title_for_matching(title_str):
    if not title_str:
        return ""
    normalized = str(title_str).lower()
    sorted_fluff = sorted(list(set(LITERAL_FLUFF_TERMS)), key=len, reverse=True)
    for term in sorted_fluff:
        normalized = re.sub(re.escape(term.lower()), ' ', normalized)
    for pattern_re in REGEX_PATTERNS_POST_FLUFF:
        normalized = pattern_re.sub(' ', normalized)
    normalized = re.sub(r'[^\w\s-]', '', normalized) 
    normalized = " ".join(normalized.split())
    return normalized.strip()

# --- Database Interaction Functions ---
def get_db_connection(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def get_primary_artist_for_mv(conn, mv_id_param):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT artist_id FROM music_video_artist_link
        WHERE mv_id = ? AND artist_order = 1
        LIMIT 1
    """, (mv_id_param,))
    row = cursor.fetchone()
    return row['artist_id'] if row else None

def get_artist_name(conn, artist_id_param):
    cursor = conn.cursor()
    cursor.execute("SELECT artist_name FROM artists WHERE artist_id = ?", (artist_id_param,))
    row = cursor.fetchone()
    return row['artist_name'] if row else "Unknown Artist"

def get_songs_for_artist(conn, artist_id_param):
    print(f"DEBUG (get_songs_for_artist): Fetching songs for artist_id: {artist_id_param}")
    cursor = conn.cursor()
    query = """
        SELECT s.song_id, s.song_title
        FROM songs s
        JOIN song_artist_link sal ON s.song_id = sal.song_id
        WHERE sal.artist_id = ?
    """
    print(f"DEBUG (get_songs_for_artist): Executing query: {query.strip()} with params: ({artist_id_param},)")
    try:
        cursor.execute(query, (artist_id_param,))
    except sqlite3.Error as e_inner:
        print(f"DEBUG (get_songs_for_artist): Error during execute: {e_inner}")
        raise
    songs = []
    raw_songs = cursor.fetchall()
    print(f"DEBUG (get_songs_for_artist): Fetched {len(raw_songs)} raw songs from DB.")
    if raw_songs:
        for row in raw_songs:
            normalized = normalize_title_for_matching(row['song_title'])
            if normalized: 
                songs.append({
                    'song_id': row['song_id'],
                    'original_title': row['song_title'],
                    'normalized_title': normalized
                })
    print(f"DEBUG (get_songs_for_artist): Returning {len(songs)} processed songs.")
    return songs

def get_existing_links(conn, mv_id_param):
    cursor = conn.cursor()
    # CORRECTED: Use music_video_id column from song_music_video_link
    cursor.execute("SELECT song_id FROM song_music_video_link WHERE music_video_id = ?", (mv_id_param,))
    return [row['song_id'] for row in cursor.fetchall()]

def delete_links_for_mv(conn, mv_id_param):
    cursor = conn.cursor()
    # CORRECTED: Use music_video_id column from song_music_video_link
    cursor.execute("DELETE FROM song_music_video_link WHERE music_video_id = ?", (mv_id_param,))

def insert_links(conn, mv_id_param, song_ids_to_link):
    cursor = conn.cursor()
    for song_id in song_ids_to_link:
        try:
            # CORRECTED: Use music_video_id column from song_music_video_link
            cursor.execute("INSERT INTO song_music_video_link (music_video_id, song_id) VALUES (?, ?)", (mv_id_param, song_id))
        except sqlite3.IntegrityError:
            print(f"Warning: Link for MV ID {mv_id_param} and Song ID {song_id} already exists or other integrity error.")

def update_mv_last_checked(conn, mv_id_param):
    cursor = conn.cursor()
    timestamp = datetime.now(timezone.utc).isoformat()
    cursor.execute("UPDATE music_videos SET last_checked_at = ? WHERE mv_id = ?", (timestamp, mv_id_param))

# --- Main Processing Logic ---
def process_music_videos():
    conn = None
    try:
        conn = get_db_connection(NEW_DB_PATH)
        print("--- Music Video to Song Linker ---")
        while True:
            mode = input("Choose mode: (U)pdate unchecked MVs, (R)echeck all MVs, (Q)uit: ").upper()
            if mode in ['U', 'R', 'Q']:
                break
            print("Invalid choice. Please enter U, R, or Q.")
        if mode == 'Q':
            print("Exiting.")
            return

        mv_fetch_query = "SELECT mv_id, title FROM music_videos"
        if mode == 'U':
            mv_fetch_query += " WHERE last_checked_at IS NULL ORDER BY mv_id"
        else: 
            mv_fetch_query += " ORDER BY mv_id"

        cursor = conn.cursor()
        cursor.execute(mv_fetch_query)
        music_videos_to_process = cursor.fetchall()

        if not music_videos_to_process:
            print("No music videos to process in the selected mode.")
            return
        print(f"Found {len(music_videos_to_process)} music videos to process.")

        for mv_row in music_videos_to_process:
            mv_id = mv_row['mv_id']
            original_mv_title = mv_row['title']
            normalized_mv_title = normalize_title_for_matching(original_mv_title)

            print(f"\n---------------------------------------------------------")
            print(f"Processing MV ID: {mv_id} | Title: {original_mv_title}")
            if not normalized_mv_title:
                print("MV title normalized to empty string. Skipping.")
                update_mv_last_checked(conn, mv_id)
                conn.commit()
                continue
            print(f"Normalized MV Title: '{normalized_mv_title}'")

            primary_artist_id = get_primary_artist_for_mv(conn, mv_id)
            if not primary_artist_id:
                print(f"Error: No primary artist (order=1) found for MV ID {mv_id}. Please check `music_video_artist_link`. Skipping.")
                continue
            
            artist_name = get_artist_name(conn, primary_artist_id)
            print(f"Primary Artist: {artist_name} (ID: {primary_artist_id})") # This was the last successful print in your trace

            print(f"DEBUG: About to call get_songs_for_artist for artist_id: {primary_artist_id}")
            artist_songs = get_songs_for_artist(conn, primary_artist_id)
            print(f"DEBUG: Call to get_songs_for_artist completed. Found {len(artist_songs) if artist_songs else 0} songs.")

            if not artist_songs:
                print(f"No songs found for artist {artist_name}. Skipping MV.")
                update_mv_last_checked(conn, mv_id)
                conn.commit()
                continue

            existing_song_ids = get_existing_links(conn, mv_id) # Uses corrected column name
            if mode == 'R' and existing_song_ids:
                print(f"MV already has {len(existing_song_ids)} link(s).")
                while True:
                    reeval_choice = input("Re-evaluate and replace existing links? (y/n): ").lower()
                    if reeval_choice == 'y':
                        delete_links_for_mv(conn, mv_id) # Uses corrected column name
                        print("Existing links deleted.")
                        break
                    elif reeval_choice == 'n':
                        print("Skipping re-evaluation for this MV.")
                        update_mv_last_checked(conn, mv_id)
                        conn.commit()
                        break 
                if reeval_choice == 'n':
                    continue

            # ---- MATCHING LOGIC WILL GO HERE (Phase 2) ----
            print(f"Found {len(artist_songs)} songs by {artist_name} for potential matching.")
            # For now, insert_links won't be called yet until Phase 2 matching is built.

            cont = input("TEMP: Press Enter to continue to next MV, or 'q' to quit loop: ")
            if cont.lower() == 'q':
                break
        print("\n--- Processing Complete ---")

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        # import traceback # Uncomment for full traceback
        # traceback.print_exc() 
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        # import traceback # Uncomment for full traceback
        # traceback.print_exc()
    finally:
        if conn:
            conn.close()
            print("Database connection closed.")

if __name__ == '__main__':
    process_music_videos()
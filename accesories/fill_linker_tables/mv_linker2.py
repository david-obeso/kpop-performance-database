import sqlite3
import os
import re
from datetime import datetime, timezone

# --- Configuration ---
NEW_DB_PATH = 'KpopDatabase_new.db' # Ensure this path is correct

# --- Normalization Fluff & Function ---
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
    re.compile(r'\s*\([^)]*\)\s*'), # Remove content in parentheses
    re.compile(r'\s*\[[^\]]*\]\s*')  # Remove content in brackets
]

def normalize_title_for_matching(title_str):
    if not title_str:
        return ""
    normalized = str(title_str).lower()
    # Sort fluff terms by length in descending order to remove longer phrases first
    sorted_fluff = sorted(list(set(LITERAL_FLUFF_TERMS)), key=len, reverse=True)
    for term in sorted_fluff:
        # Replace with space to avoid merging words and handle terms at ends of strings
        normalized = re.sub(r'(?:^|\s)' + re.escape(term.lower()) + r'(?:$|\s)', ' ', normalized)
        normalized = re.sub(re.escape(term.lower()), ' ', normalized) # General replacement as fallback

    # Apply regex patterns that remove bracketed/parenthesized content
    for pattern_re in REGEX_PATTERNS_POST_FLUFF:
        normalized = pattern_re.sub(' ', normalized)

    # Remove special characters except hyphen (allow words like "sci-fi") and apostrophe (for contractions)
    # CORRECTED REGEX: Move hyphen to the end of the character set, or escape it.
    normalized = re.sub(r"[^\w\s'-]", '', normalized) # Keep apostrophe and hyphen
    # Normalize whitespace (replace multiple spaces/tabs/newlines with a single space)
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
    # print(f"DEBUG (get_songs_for_artist): Fetching songs for artist_id: {artist_id_param}")
    cursor = conn.cursor()
    query = """
        SELECT s.song_id, s.song_title
        FROM songs s
        JOIN song_artist_link sal ON s.song_id = sal.song_id
        WHERE sal.artist_id = ?
        ORDER BY s.song_title COLLATE NOCASE
    """ # Added ORDER BY for consistent display
    try:
        cursor.execute(query, (artist_id_param,))
    except sqlite3.Error as e_inner:
        print(f"DEBUG (get_songs_for_artist): Error during execute: {e_inner}")
        raise
    songs = []
    raw_songs = cursor.fetchall()
    if raw_songs:
        for row in raw_songs:
            normalized = normalize_title_for_matching(row['song_title'])
            if normalized: # Only add songs that have a non-empty normalized title
                songs.append({
                    'song_id': row['song_id'],
                    'original_title': row['song_title'],
                    'normalized_title': normalized
                })
    return songs


def get_existing_links(conn, mv_id_param):
    cursor = conn.cursor()
    cursor.execute("SELECT song_id FROM song_music_video_link WHERE music_video_id = ?", (mv_id_param,))
    return [row['song_id'] for row in cursor.fetchall()]

def delete_links_for_mv(conn, mv_id_param):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM song_music_video_link WHERE music_video_id = ?", (mv_id_param,))

def insert_links(conn, mv_id_param, song_ids_to_link):
    cursor = conn.cursor()
    for song_id in song_ids_to_link:
        try:
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
        else: # mode == 'R'
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
            reeval_choice_input_flag = 'y' # Default to allow processing, 'n' if user skips re-evaluation

            print(f"\n---------------------------------------------------------")
            print(f"Processing MV ID: {mv_id} | Title: {original_mv_title}")

            normalized_mv_title = normalize_title_for_matching(original_mv_title)
            if not normalized_mv_title:
                print(f"MV title '{original_mv_title}' normalized to empty string. Skipping.")
                update_mv_last_checked(conn, mv_id)
                conn.commit()
                continue
            print(f"Normalized MV Title: '{normalized_mv_title}'")

            primary_artist_id = get_primary_artist_for_mv(conn, mv_id)
            if not primary_artist_id:
                print(f"Error: No primary artist (order=1) found for MV ID {mv_id}. Please check `music_video_artist_link`. Skipping.")
                update_mv_last_checked(conn, mv_id) # Mark as checked to avoid re-processing if it's a data issue
                conn.commit()
                continue
            
            artist_name = get_artist_name(conn, primary_artist_id)
            print(f"Primary Artist: {artist_name} (ID: {primary_artist_id})")

            artist_songs = get_songs_for_artist(conn, primary_artist_id)
            if not artist_songs:
                print(f"No songs found for artist '{artist_name}'. Skipping MV.")
                update_mv_last_checked(conn, mv_id)
                conn.commit()
                continue
            
            # Handle re-evaluation for 'R' mode
            if mode == 'R':
                existing_song_ids = get_existing_links(conn, mv_id)
                if existing_song_ids:
                    print(f"MV ID {mv_id} ('{original_mv_title}') already has {len(existing_song_ids)} link(s).")
                    while True:
                        reeval_choice_input = input(f"  Re-evaluate and replace existing links? (y/n, default n): ").strip().lower()
                        if not reeval_choice_input: reeval_choice_input = 'n'

                        if reeval_choice_input == 'y':
                            delete_links_for_mv(conn, mv_id)
                            print("  Existing links deleted. Proceeding with re-evaluation.")
                            reeval_choice_input_flag = 'y'
                            break 
                        elif reeval_choice_input == 'n':
                            print("  Skipping re-evaluation for this MV. Existing links will be kept.")
                            update_mv_last_checked(conn, mv_id)
                            conn.commit()
                            reeval_choice_input_flag = 'n'
                            break 
                        else:
                            print("  Invalid input. Please enter 'y' or 'n'.")
                    if reeval_choice_input_flag == 'n':
                        continue # Skip to the next MV in the main loop

            # ---- MATCHING LOGIC ----
            perfect_matches = []
            for song in artist_songs:
                if song['normalized_title'] == normalized_mv_title:
                    perfect_matches.append(song)

            songs_to_link_ids = []

            if perfect_matches:
                if len(perfect_matches) == 1:
                    song = perfect_matches[0]
                    print(f"Perfect match found: '{song['original_title']}' (ID: {song['song_id']})")
                    songs_to_link_ids.append(song['song_id'])
                else: # Multiple perfect matches
                    print(f"Multiple perfect matches found for MV '{original_mv_title}' (Normalized: '{normalized_mv_title}'):")
                    for i, song in enumerate(perfect_matches):
                        print(f"  {i+1}. {song['original_title']} (ID: {song['song_id']})")
                    
                    while True:
                        choice = input(f"  Enter song numbers to link (comma-separated, e.g., 1,2), (L)ink all listed, or (S)kip: ").strip().lower()
                        if choice == 's':
                            print("  Skipping linking for this MV based on user choice.")
                            break
                        if choice == 'l':
                            songs_to_link_ids = [s['song_id'] for s in perfect_matches]
                            print(f"  Linking all {len(songs_to_link_ids)} listed perfect matches.")
                            break
                        try:
                            selected_indices = [int(x.strip()) - 1 for x in choice.split(',') if x.strip()]
                            temp_song_ids = []
                            valid_selection = True
                            for idx in selected_indices:
                                if 0 <= idx < len(perfect_matches):
                                    temp_song_ids.append(perfect_matches[idx]['song_id'])
                                else:
                                    valid_selection = False
                                    print(f"  Invalid selection: {idx+1}. Please choose from 1 to {len(perfect_matches)}.")
                                    break
                            if valid_selection and temp_song_ids:
                                songs_to_link_ids.extend(temp_song_ids)
                                print(f"  Selected {len(temp_song_ids)} song(s) to link.")
                                break
                            elif not temp_song_ids and valid_selection :
                                print("  No songs selected. Please enter valid numbers, 'l', or 's'.")
                            elif not valid_selection:
                                pass 
                        except ValueError:
                            print("  Invalid input. Please use numbers, commas, 'l', or 's'.")
            else: # No perfect matches
                print(f"No perfect match found for MV '{original_mv_title}' (Normalized: '{normalized_mv_title}').")
                print(f"Please choose from the {len(artist_songs)} songs by {artist_name} (or (S)kip):")
                for i, song in enumerate(artist_songs): # Show all songs by the artist
                    print(f"  {i+1}. {song['original_title']} (Normalized: '{song['normalized_title']}') (ID: {song['song_id']})")

                while True:
                    user_input = input(f"  Enter song numbers to link (comma-separated), or (S)kip: ").strip().lower()
                    if user_input == 's':
                        print("  Skipping linking for this MV based on user choice.")
                        break
                    if not user_input:
                        print("  No selection made. Please enter numbers or 's'.")
                        continue
                    try:
                        selected_indices = [int(x.strip()) - 1 for x in user_input.split(',') if x.strip()]
                        temp_song_ids = []
                        valid_selection = True
                        for idx in selected_indices:
                            if 0 <= idx < len(artist_songs):
                                temp_song_ids.append(artist_songs[idx]['song_id'])
                            else:
                                valid_selection = False
                                print(f"  Invalid selection: {idx+1}. Please choose from 1 to {len(artist_songs)}.")
                                break
                        if valid_selection and temp_song_ids:
                            songs_to_link_ids.extend(temp_song_ids)
                            print(f"  Selected {len(temp_song_ids)} song(s) to link.")
                            break
                        elif not temp_song_ids and valid_selection:
                             print("  No songs selected. Please enter valid numbers or 's'.")
                        elif not valid_selection:
                            pass
                    except ValueError:
                        print("  Invalid input. Please use numbers, commas, or 's'.")
            
            # Ensure uniqueness of song IDs before inserting
            songs_to_link_ids = list(set(songs_to_link_ids))

            if songs_to_link_ids:
                print(f"Attempting to link MV ID {mv_id} to Song IDs: {songs_to_link_ids}")
                insert_links(conn, mv_id, songs_to_link_ids)
            else:
                # Avoid "No songs selected" if user explicitly chose not to re-evaluate and no other links were made
                if not (mode == 'R' and reeval_choice_input_flag == 'n'):
                     print(f"No songs were ultimately selected or available to link for MV ID {mv_id}.")


            update_mv_last_checked(conn, mv_id)
            conn.commit() # Commit after each MV is processed

        print("\n--- Processing Complete ---")

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        import traceback
        traceback.print_exc() 
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if conn:
            conn.close()
            print("Database connection closed.")

if __name__ == '__main__':
    process_music_videos()
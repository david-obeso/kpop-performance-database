import sqlite3
import os
import re
from datetime import datetime, timezone
from collections import OrderedDict

# --- Configuration ---
NEW_DB_PATH = 'KpopDatabase_new.db' # Ensure this path is correct

# --- Normalization Fluff & Function (Use and extend this list for performances!) ---
LITERAL_FLUFF_TERMS = [
    # Existing from MV (review and keep relevant, add performance-specific)
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
    "mv", "music video", "official video", "official mv", # Less common in perf titles
    "perf. video", "lyric video", "special video", "live clip", "self cam",
    "(official)", "(performance)", "(live)", "(acoustic)",
    "ver.", "version", "ver",
    "dance practice", "안무영상", "뮤직비디오",
    # Performance specific additions (EXAMPLES - EXPAND THIS LIST SIGNIFICANTLY!)
    "live at", "live version", "live ver", "encore", "medley", "acoustic session",
    "unplugged", "showcase", "fanmeeting", "concert", "kcon", "mama awards",
    "inkigayo", "m countdown", "music bank", "the show", "show champion", "simply k-pop",
    "comeback stage", "goodbye stage", "debut stage",
    "fancam", "facecam", "full cam", "vertical cam",
    "(japanese version)", "(korean version)", "(english version)", "(original version)",
    "(band version)", "(acoustic version)", "(remix version)",
    # Common patterns that might be caught by regex but explicit can help
    "| sbs", "| kbs", "| mbc",
    # Dated fluff (the regex `\s*\([^)]*\)\s*` and `\s*\[[^\]]*\]\s*` will catch dates in brackets/parens)
    # You might consider adding regex for specific date formats if they are outside brackets/parens
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
    # Use a copy of the list for sorting if it's modified elsewhere, or ensure it's defined fresh.
    # For this script, LITERAL_FLUFF_TERMS is global and static per run.
    sorted_fluff = sorted(list(set(LITERAL_FLUFF_TERMS)), key=len, reverse=True)

    for term in sorted_fluff:
        normalized = re.sub(r'(?:^|\s)' + re.escape(term.lower()) + r'(?:$|\s)', ' ', normalized, flags=re.IGNORECASE)
        normalized = re.sub(re.escape(term.lower()), ' ', normalized, flags=re.IGNORECASE)

    for pattern_re in REGEX_PATTERNS_POST_FLUFF:
        normalized = pattern_re.sub(' ', normalized)

    normalized = re.sub(r"[^\w\s'-]", '', normalized) # Keep apostrophe and hyphen
    normalized = " ".join(normalized.split())
    return normalized.strip()

# --- Global Cache for User Decisions ---
# Key: (normalized_song_mention, primary_artist_id)
# Value: list of song_ids (empty list means user explicitly skipped this mention for this artist)
user_decision_cache = {}

# --- Database Interaction Functions ---
def get_db_connection(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def get_primary_artist_for_performance(conn, performance_id_param):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT artist_id FROM performance_artist_link
        WHERE performance_id = ? AND artist_order = 1
        LIMIT 1
    """, (performance_id_param,))
    row = cursor.fetchone()
    return row['artist_id'] if row else None

def get_artist_name(conn, artist_id_param): # Reusable
    cursor = conn.cursor()
    cursor.execute("SELECT artist_name FROM artists WHERE artist_id = ?", (artist_id_param,))
    row = cursor.fetchone()
    return row['artist_name'] if row else "Unknown Artist"

artist_songs_cache = {} # Cache songs per artist to avoid repeated DB calls for the same artist

def get_songs_for_artist(conn, artist_id_param): # Reusable, with caching
    if artist_id_param in artist_songs_cache:
        return artist_songs_cache[artist_id_param]

    cursor = conn.cursor()
    query = """
        SELECT s.song_id, s.song_title
        FROM songs s
        JOIN song_artist_link sal ON s.song_id = sal.song_id
        WHERE sal.artist_id = ?
        ORDER BY s.song_title COLLATE NOCASE
    """
    cursor.execute(query, (artist_id_param,))
    songs = []
    raw_songs = cursor.fetchall()
    if raw_songs:
        for row in raw_songs:
            normalized = normalize_title_for_matching(row['song_title'])
            if normalized:
                songs.append({
                    'song_id': row['song_id'],
                    'original_title': row['song_title'],
                    'normalized_title': normalized
                })
    artist_songs_cache[artist_id_param] = songs # Cache the result
    return songs

def get_existing_performance_links(conn, performance_id_param):
    cursor = conn.cursor()
    cursor.execute("SELECT song_id FROM song_performance_link WHERE performance_id = ?", (performance_id_param,))
    return [row['song_id'] for row in cursor.fetchall()]

def delete_links_for_performance(conn, performance_id_param):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM song_performance_link WHERE performance_id = ?", (performance_id_param,))

def insert_performance_links(conn, performance_id_param, song_ids_to_link):
    cursor = conn.cursor()
    for song_id in song_ids_to_link:
        try:
            cursor.execute("INSERT INTO song_performance_link (performance_id, song_id) VALUES (?, ?)", (performance_id_param, song_id))
        except sqlite3.IntegrityError:
            print(f"Warning: Link for Performance ID {performance_id_param} and Song ID {song_id} already exists or other integrity error.")

def update_performance_last_checked(conn, performance_id_param):
    cursor = conn.cursor()
    timestamp = datetime.now(timezone.utc).isoformat()
    cursor.execute("UPDATE performances SET last_checked_at = ? WHERE performance_id = ?", (timestamp, performance_id_param))

# --- Main Processing Logic ---
def process_performances():
    global user_decision_cache # Allow modification of global cache
    conn = None
    try:
        conn = get_db_connection(NEW_DB_PATH)
        print("--- Performance to Song Linker ---")
        while True:
            mode = input("Choose mode: (U)pdate unchecked Performances, (R)echeck all Performances, (Q)uit: ").upper()
            if mode in ['U', 'R', 'Q']:
                break
            print("Invalid choice. Please enter U, R, or Q.")

        if mode == 'Q':
            print("Exiting.")
            return

        perf_fetch_query = "SELECT performance_id, title FROM performances"
        if mode == 'U':
            perf_fetch_query += " WHERE last_checked_at IS NULL ORDER BY performance_id"
        else: # mode == 'R'
            perf_fetch_query += " ORDER BY performance_id"

        cursor = conn.cursor()
        cursor.execute(perf_fetch_query)
        performances_to_process = cursor.fetchall()

        if not performances_to_process:
            print("No performances to process in the selected mode.")
            return
        print(f"Found {len(performances_to_process)} performances to process.")

        for perf_row_idx, perf_row in enumerate(performances_to_process):
            perf_id = perf_row['performance_id']
            original_perf_title = perf_row['title']
            user_skipped_reevaluation_for_perf = False

            print(f"\n---------------------------------------------------------")
            print(f"Processing Performance {perf_row_idx + 1}/{len(performances_to_process)}: ID {perf_id} | Title: {original_perf_title}")

            if original_perf_title and original_perf_title.lower().startswith("multiple songs"):
                print(f"  Title starts with 'Multiple songs'. Skipping automatically.")
                update_performance_last_checked(conn, perf_id)
                conn.commit()
                continue

            primary_artist_id = get_primary_artist_for_performance(conn, perf_id)
            if not primary_artist_id:
                print(f"  Error: No primary artist (order=1) found for Performance ID {perf_id}. Skipping.")
                update_performance_last_checked(conn, perf_id)
                conn.commit()
                continue
            
            artist_name = get_artist_name(conn, primary_artist_id)
            print(f"  Primary Artist: {artist_name} (ID: {primary_artist_id})")

            # Handle re-evaluation for 'R' mode for the whole performance
            if mode == 'R':
                existing_song_ids = get_existing_performance_links(conn, perf_id)
                if existing_song_ids:
                    print(f"  Performance ID {perf_id} already has {len(existing_song_ids)} link(s).")
                    while True:
                        reeval_choice = input(f"    Re-evaluate and replace existing links for this entire performance? (y/n, default n): ").strip().lower()
                        if not reeval_choice: reeval_choice = 'n'
                        if reeval_choice == 'y':
                            delete_links_for_performance(conn, perf_id)
                            print("    Existing links for this performance deleted. Proceeding with re-evaluation.")
                            break 
                        elif reeval_choice == 'n':
                            print("    Skipping re-evaluation for this performance. Existing links kept.")
                            user_skipped_reevaluation_for_perf = True
                            break 
                        else:
                            print("    Invalid input. Please enter 'y' or 'n'.")
                    if user_skipped_reevaluation_for_perf:
                        update_performance_last_checked(conn, perf_id)
                        conn.commit()
                        continue
            
            # Split performance title into potential song mentions
            # A more sophisticated split might be needed if song titles themselves contain commas
            # not intended as separators. For now, simple split by comma.
            raw_song_mentions = [s.strip() for s in original_perf_title.split(',') if s.strip()]
            if not raw_song_mentions:
                 raw_song_mentions = [original_perf_title.strip()] # If no commas, treat whole title as one mention

            all_linked_song_ids_for_this_perf = set()
            
            artist_songs = get_songs_for_artist(conn, primary_artist_id) # Fetch once for the artist
            if not artist_songs:
                print(f"  No songs found for artist '{artist_name}'. Cannot link songs for this performance. Skipping.")
                update_performance_last_checked(conn, perf_id)
                conn.commit()
                continue

            for mention_idx, raw_mention in enumerate(raw_song_mentions):
                print(f"  Segment {mention_idx + 1}/{len(raw_song_mentions)}: '{raw_mention}'")
                normalized_mention = normalize_title_for_matching(raw_mention)

                if not normalized_mention:
                    print(f"    Segment normalized to empty string. Skipping this segment.")
                    continue
                print(f"    Normalized segment: '{normalized_mention}'")

                cache_key = (normalized_mention, primary_artist_id)
                segment_song_ids = []

                if cache_key in user_decision_cache:
                    cached_ids = user_decision_cache[cache_key]
                    if cached_ids: # Non-empty list means link these
                        print(f"    Using cached decision: Linking to Song IDs {cached_ids}")
                        segment_song_ids.extend(cached_ids)
                    else: # Empty list means user previously skipped this segment
                        print(f"    Using cached decision: User previously skipped this segment.")
                    all_linked_song_ids_for_this_perf.update(segment_song_ids)
                    continue # Move to the next segment

                # --- If not in cache, perform matching for this segment ---
                perfect_matches_for_segment = []
                for song in artist_songs: # Iterate over songs of the primary artist
                    if song['normalized_title'] == normalized_mention:
                        perfect_matches_for_segment.append(song)
                
                if perfect_matches_for_segment:
                    print(f"    Perfect match(es) found for segment. Linking automatically:")
                    for song in perfect_matches_for_segment:
                        print(f"      - '{song['original_title']}' (ID: {song['song_id']})")
                        segment_song_ids.append(song['song_id'])
                    user_decision_cache[cache_key] = segment_song_ids # Cache this auto-decision
                else:
                    # No perfect match for this segment, ask user
                    print(f"    No perfect match for segment. Please choose from songs by {artist_name} (or (S)kip segment):")
                    
                    # Group artist's songs by original_title for consolidated display
                    songs_by_original_display_title = OrderedDict()
                    for song in artist_songs:
                        ot = song['original_title']
                        if ot not in songs_by_original_display_title:
                            songs_by_original_display_title[ot] = {'song_ids': [], 'normalized_titles_set': set()}
                        songs_by_original_display_title[ot]['song_ids'].append(song['song_id'])
                        songs_by_original_display_title[ot]['normalized_titles_set'].add(song['normalized_title'])
                    
                    displayable_song_groups = []
                    for original_title, data in songs_by_original_display_title.items():
                         displayable_song_groups.append({
                            'display_title': original_title,
                            'related_song_ids': sorted(list(set(data['song_ids']))),
                            'normalized_variants_display': ", ".join(sorted(list(data['normalized_titles_set'])))
                        })

                    for i, group in enumerate(displayable_song_groups):
                        id_count_hint = f" (links {len(group['related_song_ids'])} song ID(s))" if len(group['related_song_ids']) > 1 else ""
                        norm_hint = group['normalized_variants_display']
                        print(f"      {i+1}. {group['display_title']}{id_count_hint} (Normalized as: '{norm_hint}')")

                    while True:
                        user_input = input(f"      Enter song numbers for this segment (comma-separated), or (S)kip segment: ").strip().lower()
                        if user_input == 's':
                            print(f"    User skipped segment '{raw_mention}'. Caching this decision.")
                            user_decision_cache[cache_key] = [] # Cache skip decision (empty list)
                            break 
                        if not user_input:
                            print("      No selection made. Please enter numbers or 's'.")
                            continue
                        try:
                            selected_indices = [int(x.strip()) - 1 for x in user_input.split(',') if x.strip()]
                            temp_segment_ids = []
                            valid_selection = True
                            for idx in selected_indices:
                                if 0 <= idx < len(displayable_song_groups):
                                    temp_segment_ids.extend(displayable_song_groups[idx]['related_song_ids'])
                                else:
                                    valid_selection = False
                                    print(f"      Invalid selection: {idx+1}. Please choose from 1 to {len(displayable_song_groups)}.")
                                    break
                            if valid_selection and temp_segment_ids:
                                segment_song_ids.extend(list(set(temp_segment_ids))) # Add unique IDs
                                print(f"    User selected Song IDs {segment_song_ids} for this segment. Caching.")
                                user_decision_cache[cache_key] = segment_song_ids # Cache user's choice
                                break
                            elif not temp_segment_ids and valid_selection:
                                print("      No songs selected. Please enter valid numbers or 's'.")
                        except ValueError:
                            print("      Invalid input. Please use numbers, commas, or 's'.")
                
                all_linked_song_ids_for_this_perf.update(segment_song_ids)
            # --- End of segment processing ---

            if all_linked_song_ids_for_this_perf:
                unique_song_ids_to_link = sorted(list(all_linked_song_ids_for_this_perf))
                print(f"  Attempting to link Performance ID {perf_id} to Song IDs: {unique_song_ids_to_link}")
                insert_performance_links(conn, perf_id, unique_song_ids_to_link)
            else:
                if not user_skipped_reevaluation_for_perf:
                    print(f"  No songs were ultimately linked for Performance ID {perf_id}.")

            update_performance_last_checked(conn, perf_id)
            conn.commit() # Commit after each performance is fully processed (all its segments)

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
    process_performances()
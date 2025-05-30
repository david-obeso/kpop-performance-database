# db_operations.py
import sqlite3
import config # To get DATABASE_FILE

_connection = None # Module-level variable to hold the connection

def get_db_connection():
    """Establishes and/or returns the database connection."""
    global _connection
    # print("DEBUG: db_operations.get_db_connection() called.")
    if _connection is None:
        # print("DEBUG: db_operations - No existing connection, attempting to connect.")
        try:
            _connection = sqlite3.connect(config.DATABASE_FILE)
            print(f"Database connection established to {config.DATABASE_FILE}") # Keep this one
        except sqlite3.Error as e:
            print(f"Error connecting to database: {e}")
            _connection = None 
            return None
    # else:
        # print("DEBUG: db_operations - Returning existing connection.")
    return _connection

def close_db_connection():
    """Closes the database connection if it's open."""
    global _connection
    # print("DEBUG: db_operations.close_db_connection() called.")
    if _connection:
        _connection.close()
        _connection = None
        print("Database connection closed.") # Keep this one
    # else:
        # print("DEBUG: db_operations - No connection to close.")

def get_all_artists():
    """Fetches all artists from the database, ordered by name."""
    # print("DEBUG: db_operations.get_all_artists() called.")
    conn = get_db_connection()
    if not conn:
        # print("DEBUG: db_operations.get_all_artists - No DB connection.")
        return [] 
    
    artists = []
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT artist_id, artist_name FROM artists ORDER BY artist_name")
        artists = [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]
        # print(f"DEBUG: db_operations.get_all_artists - Found {len(artists)} artists.")
    except sqlite3.Error as e:
        print(f"Database error in get_all_artists: {e}")
    except AttributeError as e: 
        print(f"AttributeError in get_all_artists (likely conn is None): {e}")
    return artists

def get_all_performances_raw():
    """
    Fetches raw performance data along with concatenated artists and songs.
    Returns a list of tuples directly from the database query.
    """
    # print("DEBUG: db_operations.get_all_performances_raw() called.")
    conn = get_db_connection()
    if not conn:
        # print("DEBUG: db_operations.get_all_performances_raw - No DB connection.")
        return []

    query = """
        SELECT
            p.performance_id, p.title, p.performance_date, p.show_type, p.resolution,
            p.file_path1, p.file_path2, p.file_url, p.score,
            (SELECT GROUP_CONCAT(a.artist_name, ', ')
             FROM artists a JOIN performance_artist_link pal ON a.artist_id = pal.artist_id
             WHERE pal.performance_id = p.performance_id ORDER BY pal.artist_order, a.artist_name) AS artists_concatenated,
            (SELECT GROUP_CONCAT(s.song_title, ', ')
             FROM songs s JOIN song_performance_link spl ON s.song_id = spl.song_id
             WHERE spl.performance_id = p.performance_id) AS songs_concatenated
        FROM performances p
        ORDER BY p.performance_date DESC, p.performance_id DESC;
    """
    performances_raw = []
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        performances_raw = cursor.fetchall()
        # print(f"DEBUG: db_operations.get_all_performances_raw - Found {len(performances_raw)} raw performance rows.")
    except sqlite3.Error as e:
        print(f"Database error in get_all_performances_raw: {e}")
    except AttributeError as e: 
        print(f"AttributeError in get_all_performances_raw (likely conn is None): {e}")
    return performances_raw

def insert_music_video(title, release_date, file_url, score, artist_names, song_titles):
    conn = get_db_connection()
    cursor = conn.cursor()
    # 1. Insert music video
    cursor.execute(
        "INSERT INTO music_videos (title, release_date, file_url, score) VALUES (?, ?, ?, ?)",
        (title, release_date, file_url, score)
    )
    mv_id = cursor.lastrowid
    # 2. Link artists
    artist_ids = []
    for idx, artist_name in enumerate(artist_names):
        cursor.execute("SELECT artist_id FROM artists WHERE artist_name = ?", (artist_name,))
        row = cursor.fetchone()
        if row:
            artist_id = row[0]
            artist_ids.append(artist_id)
            cursor.execute(
                "INSERT INTO music_video_artist_link (mv_id, artist_id, artist_order) VALUES (?, ?, ?)",
                (mv_id, artist_id, idx+1)
            )
    # 3. Link songs: fetch all relevant song_ids in one query, then batch insert
    if song_titles and artist_ids:
        # Build a set of (song_title, artist_id) pairs
        pairs = [(song_title, artist_id) for song_title in song_titles for artist_id in artist_ids]
        # Use a single query with IN clauses
        song_titles_set = tuple(set(song_titles))
        artist_ids_set = tuple(set(artist_ids))
        if song_titles_set and artist_ids_set:
            query = (
                "SELECT s.song_id FROM songs s "
                "JOIN song_artist_link sal ON s.song_id = sal.song_id "
                f"WHERE s.song_title IN ({','.join(['?']*len(song_titles_set))}) "
                f"AND sal.artist_id IN ({','.join(['?']*len(artist_ids_set))})"
            )
            cursor.execute(query, song_titles_set + artist_ids_set)
            song_ids = [row[0] for row in cursor.fetchall()]
            # Batch insert all links
            cursor.executemany(
                "INSERT OR IGNORE INTO song_music_video_link (song_id, music_video_id) VALUES (?, ?)",
                [(song_id, mv_id) for song_id in song_ids]
            )
    conn.commit()

def get_all_music_videos_raw():
    """
    Fetches raw music video data along with concatenated artists and songs, including file_path1 and file_path2 for local playback.
    Returns a list of tuples directly from the database query.
    """
    conn = get_db_connection()
    if not conn:
        return []
    query = """
        SELECT
            mv.mv_id, mv.title, mv.release_date, mv.file_url, mv.file_path1, mv.file_path2, mv.score,
            (SELECT GROUP_CONCAT(a.artist_name, ', ')
             FROM artists a JOIN music_video_artist_link mval ON a.artist_id = mval.artist_id
             WHERE mval.mv_id = mv.mv_id ORDER BY mval.artist_order, a.artist_name) AS artists_concatenated,
            (SELECT GROUP_CONCAT(s.song_title, ', ')
             FROM songs s JOIN song_music_video_link smvl ON s.song_id = smvl.song_id
             WHERE smvl.music_video_id = mv.mv_id) AS songs_concatenated
        FROM music_videos mv
        ORDER BY mv.release_date DESC, mv.mv_id DESC;
    """
    music_videos_raw = []
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        music_videos_raw = cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Database error in get_all_music_videos_raw: {e}")
    except AttributeError as e:
        print(f"AttributeError in get_all_music_videos_raw (likely conn is None): {e}")
    return music_videos_raw
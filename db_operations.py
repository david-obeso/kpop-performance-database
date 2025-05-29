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

def insert_music_video(title, release_date, file_url, score, artist_names, song_ids):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO music_videos (title, release_date, file_url, score) VALUES (?, ?, ?, ?)",
        (title, release_date, file_url, score)
    )
    mv_id = cursor.lastrowid
    # Link artists
    for idx, artist_name in enumerate(artist_names):
        cursor.execute("SELECT artist_id FROM artists WHERE artist_name = ?", (artist_name,))
        row = cursor.fetchone()
        if row:
            artist_id = row[0]
            cursor.execute(
                "INSERT INTO music_video_artist_link (mv_id, artist_id, artist_order) VALUES (?, ?, ?)",
                (mv_id, artist_id, idx+1)
            )
    # Link songs
    for song_id in song_ids:
        cursor.execute(
            "INSERT INTO song_music_video_link (song_id, music_video_id) VALUES (?, ?)",
            (song_id, mv_id)
        )
    conn.commit()
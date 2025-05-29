import pandas as pd # Importing pandas for extract data from excel file
import os # We'll use this for file paths 
import sqlite3 # Importing sqlite3 for future database operations
from sqlite3 import Error # <--- Import the Error class for better error handling
import re # Import regular expression module for path conversion
import subprocess

# --- Configuration ---
EXCEL_FILE_PATH = "/home/david/kpop-performance-database/KpopDatabase.xlsm" # The path to the Excel file

PERFORMANCES_SHEET_NAME = "TV Performances" # The exact name of the sheet in the Excel file

COLUMNS_TO_READ = ['date', 'group', 'song', 'show', 'res', 'score', 'link'] # The columns we actually want to read from the Excel sheet

# --- Database Configuration ---
DATABASE_FILE = "kpop_database.db" # Name for our SQLite database file

# SQL statements to create the tables
# We use '''triple quotes''' for multi-line strings


SQL_CREATE_GROUPS_TABLE = """ CREATE TABLE IF NOT EXISTS groups (
                                    group_id INTEGER PRIMARY KEY,
                                    group_name TEXT NOT NULL UNIQUE,
                                    group_profile TEXT,
                                    picture_path TEXT,
                                    spotify_artist_id TEXT
                                ); """

SQL_CREATE_MEMBERS_TABLE = """CREATE TABLE IF NOT EXISTS members (
                                member_id INTEGER PRIMARY KEY,
                                group_id INTEGER NOT NULL,
                                member_name TEXT NOT NULL,
                                picture_path TEXT,
                                FOREIGN KEY (group_id) REFERENCES groups (group_id)
                            );"""

SQL_CREATE_SONGS_TABLE = """CREATE TABLE IF NOT EXISTS songs (
                                song_id INTEGER PRIMARY KEY,
                                song_title TEXT NOT NULL UNIQUE
                            );"""

SQL_CREATE_PERFORMANCES_TABLE = """ CREATE TABLE IF NOT EXISTS performances (
                                    performance_id INTEGER PRIMARY KEY,
                                    group_id INTEGER NOT NULL, -- Must link to a group
                                    performance_date TEXT NOT NULL, -- Assume date always exists
                                    show_type TEXT, -- Allow missing show type
                                    resolution TEXT, -- Allow missing resolution
                                    file_path TEXT NOT NULL UNIQUE, -- UBUNTU path, assume unique & required
                                    score INTEGER, -- Allow missing score
                                    notes TEXT, -- Allow missing notes (maybe replace with song_title_raw?)
                                    FOREIGN KEY (group_id) REFERENCES groups (group_id)
                                ); """
                                # Note: We might add a 'song_title_raw' column here later if needed before song linking

SQL_CREATE_PERFORMANCE_SONGS_TABLE = """CREATE TABLE IF NOT EXISTS performance_songs (
                                        performance_id INTEGER NOT NULL,
                                        song_id INTEGER NOT NULL,
                                        FOREIGN KEY (performance_id) REFERENCES performances (performance_id),
                                        FOREIGN KEY (song_id) REFERENCES songs (song_id),
                                        PRIMARY KEY (performance_id, song_id) -- Composite PK
                                    );"""

SQL_CREATE_MUSIC_VIDEOS_TABLE = """CREATE TABLE IF NOT EXISTS music_videos (
                                    mv_id INTEGER PRIMARY KEY,
                                    group_id INTEGER NOT NULL, -- An MV should belong to a group
                                    song_id INTEGER, -- << CHANGED: Allow NULL if song is unknown
                                    release_date TEXT NOT NULL, -- Assume MVs have a release date
                                    file_path TEXT NOT NULL UNIQUE,
                                    score INTEGER,
                                    title TEXT NOT NULL, 
                                    FOREIGN KEY (group_id) REFERENCES groups (group_id),
                                    FOREIGN KEY (song_id) REFERENCES songs (song_id) -- Link is optional now
                                );"""

SQL_CREATE_FANCAMS_TABLE = """CREATE TABLE IF NOT EXISTS fancams (
                                fancam_id INTEGER PRIMARY KEY,
                                group_id INTEGER NOT NULL,
                                member_id INTEGER, -- Allow unknown member
                                performance_date TEXT NOT NULL,
                                song_id INTEGER, -- Allow unknown song
                                file_path TEXT NOT NULL UNIQUE, -- Assume unique & required
                                score INTEGER, -- Allow missing score
                                focus_details TEXT, -- Allow missing details
                                FOREIGN KEY (group_id) REFERENCES groups (group_id),
                                FOREIGN KEY (member_id) REFERENCES members (member_id),
                                FOREIGN KEY (song_id) REFERENCES songs (song_id)
                            );"""

SQL_CREATE_SONG_ARTISTS_TABLE = """CREATE TABLE IF NOT EXISTS song_artists (
                                    song_id INTEGER NOT NULL,
                                    group_id INTEGER NOT NULL,
                                    FOREIGN KEY (song_id) REFERENCES songs (song_id),
                                    FOREIGN KEY (group_id) REFERENCES groups (group_id),
                                    PRIMARY KEY (song_id, group_id)
                                );"""

# --- Path Mapping (Based on your mount script) ---
# Maps Windows Drive Letters (lowercase) to Ubuntu base paths
PATH_MAPPINGS = {
    'f:': '/home/david/windows_f_drive',
    'g:': '/home/david/windows_g_drive',
    'h:': '/home/david/windows_h_drive',
    # Add more mappings if needed
}

# --- Data Processing Functions ---

def format_date(yyyymmdd_int):
    """Converts YYMMDD integer (e.g., 160706) or YYYYMMDD to 'YYYY-MM-DD' text."""
    if pd.isna(yyyymmdd_int):
        return None # Handle missing dates if necessary
    try:
        s = str(int(yyyymmdd_int)) # Convert potential float score to int then string
        if len(s) == 5: # Assume YYMMDD, need to add leading zero if year < 10
             s = '0' + s
        if len(s) == 6: # YYMMDD format
            year_part = int(s[:2])
            month_part = s[2:4]
            day_part = s[4:6]
            # Simple assumption: years < 50 are 20xx, years >= 50 are 19xx
            # Adjust this logic if your dates span differently!
            full_year = 2000 + year_part if year_part < 50 else 1900 + year_part
            return f"{full_year}-{month_part}-{day_part}"
        elif len(s) == 8: # YYYYMMDD format
             full_year = s[:4]
             month_part = s[4:6]
             day_part = s[6:8]
             return f"{full_year}-{month_part}-{day_part}"
        else:
            print(f"Warning: Unexpected date format found: {s}")
            return None # Or return the original string, or raise an error
    except ValueError:
        print(f"Warning: Could not convert date value: {yyyymmdd_int}")
        return None

def convert_windows_path(win_path):
    """Converts a Windows path (e.g., H:\...) to its Ubuntu equivalent, or passes through URLs."""
    if pd.isna(win_path) or not isinstance(win_path, str):
        return None

    # Allow YouTube or web links
    if win_path.startswith("https://") or win_path.startswith("http://"):
        return win_path

    # Make path lowercase and normalize separators for easier matching
    win_path_lower = win_path.replace('\\', '/').lower()

    for drive_letter, ubuntu_base in PATH_MAPPINGS.items():
        if win_path_lower.startswith(drive_letter + '/'):
            # Extract the part of the path after the drive letter and separator
            relative_path = win_path[len(drive_letter)+1:].replace('\\', '/') # Use original case after drive
            # Combine Ubuntu base path with the relative path
            return os.path.join(ubuntu_base, relative_path)

    # If no mapping matched, return None (not a valid path or URL)
    print(f"Warning: No path mapping found for Windows path: {win_path}")
    return None

def clean_text(text_value):
    """Handles NaN or other non-text values, returns string or None."""
    if pd.isna(text_value):
        return None
    return str(text_value).strip() # Convert to string and remove leading/trailing whitespace

def clean_score(score_value):
    """Handles NaN score, converts valid scores to integer."""
    if pd.isna(score_value):
        return None
    try:
        return int(score_value) # Convert float (like 1.0) to integer (1)
    except ValueError:
        print(f"Warning: Could not convert score to integer: {score_value}")
        return None
    
# --- Database Functions ---

def create_connection(db_file):
    """ Create a database connection to the SQLite database specified by db_file """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        print(f"SQLite connection successful (using version {sqlite3.sqlite_version})")
        return conn
    except Error as e:
        print(f"Error connecting to database: {e}")
    return conn

def create_table(conn, create_table_sql):
    """ Create a table from the create_table_sql statement """
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
        print(f"Successfully executed table creation SQL (or table already exists).")
    except Error as e:
        print(f"Error creating table: {e}")


# --- Main Script ---

def main():
    # --- Sync OneDrive before reading Excel ---
    print("--- Syncing OneDrive to get the latest Excel file ---")
    try:
        subprocess.run(
            ["/usr/local/bin/onedrive", "--sync", "--download-only"],
            check=True
        )
        print("OneDrive sync completed.")
    except Exception as e:
        print(f"Warning: Could not sync OneDrive: {e}")

    print("--- Database Setup ---")
    conn = create_connection(DATABASE_FILE)

    if conn is not None:
        # Create all tables (assuming you added all SQL CREATE statements)
        create_table(conn, SQL_CREATE_GROUPS_TABLE)
        create_table(conn, SQL_CREATE_MEMBERS_TABLE) # Add calls for all tables
        create_table(conn, SQL_CREATE_SONGS_TABLE)
        create_table(conn, SQL_CREATE_PERFORMANCES_TABLE)
        create_table(conn, SQL_CREATE_PERFORMANCE_SONGS_TABLE)
        create_table(conn, SQL_CREATE_MUSIC_VIDEOS_TABLE)
        create_table(conn, SQL_CREATE_FANCAMS_TABLE)
        create_table(conn, SQL_CREATE_SONG_ARTISTS_TABLE)
        print("Database tables checked/created.")
    else:
        print("Error! Cannot create the database connection. Exiting.")
        return

    print("\n--- Excel Reading ---")
    try:
        if not os.path.exists(EXCEL_FILE_PATH):
            print(f"ERROR: File not found at path: {EXCEL_FILE_PATH}")
            conn.close()
            return

        performances_df = pd.read_excel(
            EXCEL_FILE_PATH,
            sheet_name=PERFORMANCES_SHEET_NAME,
            usecols=COLUMNS_TO_READ
        )
        print(f"Successfully read {len(performances_df)} rows from Excel.")

    except Exception as e:
        print(f"An error occurred during Excel reading: {e}")
        conn.close()
        return

    print("\n--- Data Processing ---")
    try:
        # Apply cleaning and conversion functions
        # Create new columns in the DataFrame for the processed data
        performances_df['processed_date'] = performances_df['date'].apply(format_date)
        performances_df['ubuntu_path'] = performances_df['link'].apply(convert_windows_path)
        performances_df['clean_group'] = performances_df['group'].apply(clean_text)
        performances_df['clean_song'] = performances_df['song'].apply(clean_text) # Keep raw song for now
        performances_df['clean_show'] = performances_df['show'].apply(clean_text)
        performances_df['clean_res'] = performances_df['res'].apply(clean_text)
        performances_df['processed_score'] = performances_df['score'].apply(clean_score)

        # Drop rows where essential info is missing after processing
        # Only drop rows where ubuntu_path is missing AND not a valid URL
        def is_valid_path_or_url(val):
            if pd.isna(val):
                return False
            if isinstance(val, str) and (val.startswith("https://") or val.startswith("http://")):
                return True
            return bool(val)

        performances_df = performances_df[
            performances_df['processed_date'].notna() &
            performances_df['clean_group'].notna() &
            performances_df['ubuntu_path'].apply(is_valid_path_or_url)
        ]

        print(f"{len(performances_df)} rows remaining after cleaning required fields.")

        print("Data processing applied. First 5 rows processed:")
        print(performances_df[['processed_date', 'clean_group', 'ubuntu_path', 'processed_score']].head())

    except Exception as e:
        print(f"An error occurred during data processing: {e}")
        conn.close()
        return


    print("\n--- Database Insertion ---")
    cursor = conn.cursor()
    inserted_groups = 0
    inserted_performances = 0
    skipped_performances = 0

    try:
        # 1. Insert Unique Groups
        unique_groups = performances_df['clean_group'].unique()
        print(f"Found {len(unique_groups)} unique group names. Inserting into 'groups' table...")
        group_map = {} # Dictionary to map group name to group_id

        for group_name in unique_groups:
            if group_name: # Ensure not None or empty string
                try:
                    # Use INSERT OR IGNORE to avoid errors if group already exists (due to UNIQUE constraint)
                    cursor.execute("INSERT OR IGNORE INTO groups (group_name) VALUES (?)", (group_name,))
                    if cursor.rowcount > 0:
                        inserted_groups += 1
                    # Get the group_id (whether newly inserted or existing)
                    cursor.execute("SELECT group_id FROM groups WHERE group_name = ?", (group_name,))
                    result = cursor.fetchone()
                    if result:
                        group_map[group_name] = result[0]
                except sqlite3.Error as group_err:
                    print(f"Error inserting/fetching group '{group_name}': {group_err}")

        print(f"Finished group insertion/mapping. {inserted_groups} new groups added.")
        conn.commit() # Commit group insertions

        # 2. Insert Performances
        print("Inserting into 'performances' table...")
        for index, row in performances_df.iterrows():
            group_id = group_map.get(row['clean_group'])

            # Skip if group_id wasn't found (shouldn't happen if group insertion worked)
            if group_id is None:
                print(f"Warning: Skipping row {index} due to missing group_id for group '{row['clean_group']}'")
                skipped_performances += 1
                continue

            # Prepare data tuple for insertion
            performance_data = (
                group_id,
                row['processed_date'],
                row['clean_show'],
                row['clean_res'],
                row['ubuntu_path'],
                row['processed_score'],
                row['clean_song'] # Use the cleaned raw song title as 'notes' for now
            )

            try:
                # Use INSERT OR IGNORE because file_path is UNIQUE
                cursor.execute("""
                    INSERT OR IGNORE INTO performances
                    (group_id, performance_date, show_type, resolution, file_path, score, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, performance_data)
                if cursor.rowcount > 0:
                    inserted_performances += 1
                else:
                    # If rowcount is 0, it means IGNORE was triggered (likely duplicate file_path)
                    skipped_performances += 1
            except sqlite3.Error as perf_err:
                 print(f"Error inserting performance row {index} ('{row['ubuntu_path']}'): {perf_err}")
                 skipped_performances += 1 # Count errors as skipped

        conn.commit() # Commit performance insertions
        print(f"Finished performance insertion.")
        print(f"  Inserted: {inserted_performances}")
        print(f"  Skipped (duplicates/errors): {skipped_performances}")

    except Exception as e:
        print(f"An error occurred during database insertion: {e}")
        conn.rollback() # Rollback any partial changes if error occurs mid-transaction

    finally:
        # --- Verification Query ---
        print("\n--- Database Verification ---")
        try:
            print("\nFirst 5 groups from database:")
            cursor.execute("SELECT group_id, group_name FROM groups LIMIT 5")
            print(cursor.fetchall())

            print("\nFirst 5 performances from database:")
            cursor.execute("SELECT performance_id, group_id, performance_date, file_path, score FROM performances LIMIT 5")
            print(cursor.fetchall())
        except Exception as e:
            print(f"An error occurred during verification query: {e}")

        # Close the connection
        if conn:
            conn.close()
            print("\nDatabase connection closed.")

# --- Main execution ---
if __name__ == "__main__":
    main()



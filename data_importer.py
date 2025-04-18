import pandas as pd # Importing pandas for extract data from excel file
import os # We'll use this for file paths 
import sqlite3 # Importing sqlite3 for future database operations
from sqlite3 import Error # <--- Import the Error class for better error handling

# --- Configuration ---
EXCEL_FILE_PATH = "/home/david/Documents/KpopDatabase_2.1.xlsm" # The path to the Excel file

PERFORMANCES_SHEET_NAME = "TV Performances" # The exact name of the sheet in the Excel file

COLUMNS_TO_READ = ['date', 'group', 'song', 'show', 'res', 'score', 'link'] # The columns we actually want to read from the Excel sheet

# --- Database Configuration ---
DATABASE_FILE = "kpop_music.db" # Name for our SQLite database file

# SQL statements to create the tables
# We use '''triple quotes''' for multi-line strings


SQL_CREATE_GROUPS_TABLE = """ CREATE TABLE IF NOT EXISTS groups (
                                    group_id INTEGER PRIMARY KEY,
                                    group_name TEXT NOT NULL UNIQUE,
                                    group_profile TEXT,
                                    picture_path TEXT
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
    """
    Main function to setup database, read Excel, and prepare data.
    """
    print("--- Database Setup ---")
    # Create a database connection
    conn = create_connection(DATABASE_FILE)

    # Create tables if they don't exist
    if conn is not None:
        create_table(conn, SQL_CREATE_GROUPS_TABLE)
        create_table(conn, SQL_CREATE_PERFORMANCES_TABLE)
        # We can close the connection for now, will reopen when inserting
        conn.close()
        print("Database tables checked/created.")
    else:
        print("Error! Cannot create the database connection.")
        return # Exit if we can't connect to the DB

    print("\n--- Excel Reading ---")
    print(f"Attempting to read sheet '{PERFORMANCES_SHEET_NAME}' from file: {EXCEL_FILE_PATH}")

    try:
        # Check if the file exists
        if not os.path.exists(EXCEL_FILE_PATH):
            print(f"ERROR: File not found at path: {EXCEL_FILE_PATH}")
            return

        # Read the Excel file
        performances_df = pd.read_excel(
            EXCEL_FILE_PATH,
            sheet_name=PERFORMANCES_SHEET_NAME,
            usecols=COLUMNS_TO_READ
        )

        print("\nSuccessfully read the specified columns from the Excel sheet!")
        print("\nColumns read:")
        print(list(performances_df.columns))
        print("\nInferred data types:")
        print(performances_df.dtypes)
        print("\nFirst 5 rows of data (raw):")
        print(performances_df.head())
        print(f"\nTotal number of performances read: {len(performances_df)}")

        # --- Data Processing (Placeholder - To be done next) ---
        print("\n--- Data Processing (Preview) ---")
        # TODO: Convert date column
        # TODO: Convert link column (WINDOWS -> UBUNTU PATH) <--- CRITICAL
        # TODO: Handle NaN in song, score
        # TODO: Extract unique groups for 'groups' table

        print("\nScript finished for now. Next steps: Data processing and insertion.")


    except FileNotFoundError:
        print(f"ERROR: FileNotFoundError. Could not find the file at: {EXCEL_FILE_PATH}")
    except ValueError as ve:
        print(f"ERROR: ValueError occurred. Did you misspell a column name in COLUMNS_TO_READ?")
        print(f"Original error: {ve}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
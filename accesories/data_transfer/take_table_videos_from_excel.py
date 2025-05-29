import sqlite3
import os
import pandas as pd # For reading .xlsm files with pandas
from datetime import datetime

# --- Configuration ---
EXCEL_PATH = 'KpopDatabase.xlsm'
SHEET_NAME = 'Music Videos'
NEW_DB_PATH = 'KpopDatabase_new.db'

# --- Helper function to identify URLs (can be reused or refined) ---
def is_url(path_string):
    if path_string is None or pd.isna(path_string): # Handle pandas NaN for empty cells
        return False
    path_string_lower = str(path_string).lower() # Ensure it's a string
    return path_string_lower.startswith('http://') or \
           path_string_lower.startswith('https://') or \
           path_string_lower.startswith('www.')

# --- Helper function to transform Windows path to Linux path ---
def transform_windows_to_linux_path(windows_path):
    if windows_path is None or pd.isna(windows_path) or not isinstance(windows_path, str):
        return None
    if windows_path.lower().startswith("g:\\music videos\\"):
        linux_path = "/home/david/windows_g_drive/Music Videos/" + windows_path[15:]
    else:
        print(f"Warning: Windows path '{windows_path}' does not start with 'G:\\Music Videos\\'. Using original path, but replacing backslashes.")
        linux_path = windows_path
    return linux_path.replace('\\', '/')

# --- Helper function to transform date format YYMMDD to YYYY-MM-DD ---
def transform_date_format(date_val_yymmdd):
    if date_val_yymmdd is None or pd.isna(date_val_yymmdd):
        return None
    try:
        # Pandas might read dates as numbers or strings
        date_str_yymmdd = str(int(date_val_yymmdd)) if isinstance(date_val_yymmdd, (int, float)) else str(date_val_yymmdd)

        if len(date_str_yymmdd) != 6:
            # Attempt to parse if it's a full date read by pandas as datetime
            if isinstance(date_val_yymmdd, datetime):
                 return date_val_yymmdd.strftime('%Y-%m-%d')
            print(f"Warning: Date '{date_str_yymmdd}' is not in YYMMDD format. Skipping date transformation.")
            return None

        year = "20" + date_str_yymmdd[:2]
        month = date_str_yymmdd[2:4]
        day = date_str_yymmdd[4:6]
        return f"{year}-{month}-{day}"
    except ValueError:
        print(f"Warning: Could not parse date '{date_val_yymmdd}'. Skipping date transformation.")
        return None
    except Exception as e:
        print(f"Error transforming date '{date_val_yymmdd}': {e}")
        return None


def migrate_music_videos_pandas():
    if not os.path.exists(EXCEL_PATH):
        print(f"Error: Excel file '{EXCEL_PATH}' not found.")
        return
    if not os.path.exists(NEW_DB_PATH):
        print(f"Error: New database '{NEW_DB_PATH}' not found.")
        return

    conn_new = None

    try:
        # Load the Excel sheet into a pandas DataFrame
        print(f"Loading Excel workbook: {EXCEL_PATH}, Sheet: {SHEET_NAME} using pandas")
        # Pandas uses 0-indexed columns by default if header=0
        # Assuming the first row (index 0) is the header.
        # Excel columns: A, B, C, D, E
        # Corresponding DataFrame columns after read (if headers are good):
        # Let's assume headers are: 'Release Date Original', 'Group Name', 'Title', 'Score', 'File Location'
        # If headers are not standard, you might need to specify column names or use iloc
        try:
            df = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME, header=0, dtype=str) # Read all as string initially
        except FileNotFoundError:
            print(f"Error: Excel file '{EXCEL_PATH}' not found by pandas.")
            return
        except ValueError as ve: # Handles sheet not found
             print(f"Error reading Excel sheet: {ve}")
             return


        # Connect to the new database
        conn_new = sqlite3.connect(NEW_DB_PATH)
        cur_new = conn_new.cursor()

        print(f"Starting music video migration from DataFrame (read from Excel, {len(df)} rows)...")
        migrated_count = 0
        link_count = 0
        error_count = 0
        skipped_artist_not_found = []

        # Iterate over rows in the DataFrame
        for index, row in df.iterrows():
            # Access data by column name (ensure these match your Excel headers)
            # Adjust these names based on the actual headers in your Excel file's first row
            # For robustness, it's better to use actual header names.
            # If column names are "Column A", "Column B", etc. use those.
            # If they are meaningful like "Date", "Artist", "Track Title", "Rating", "Path" use them.
            # For this example, I'll assume generic names if you don't have clear headers,
            # or if you prefer to use iloc (integer location) later.
            # Let's assume your Excel sheet has headers. If not, pandas assigns 0, 1, 2...
            # I'll use column positions for now, assuming headers are present but we map by position.
            # Column A: 0, B: 1, C: 2, D: 3, E: 4
            try:
                excel_release_date_yymmdd = row.iloc[0] # Column A
                group_name_excel = row.iloc[1]          # Column B
                title_excel = row.iloc[2]               # Column C
                score_excel = row.iloc[3]               # Column D
                file_location_excel = row.iloc[4]       # Column E

                # --- 1. Prepare data for new 'music_videos' table ---
                title = str(title_excel).strip() if not pd.isna(title_excel) else None
                release_date = transform_date_format(excel_release_date_yymmdd)

                # Score: ensure it's an int or None
                score = None
                if not pd.isna(score_excel):
                    try:
                        score = int(float(score_excel)) # float first to handle "X.0"
                    except ValueError:
                        print(f"Warning: Row {index + 2} in Excel: Could not convert score '{score_excel}' to integer for MV '{title}'. Setting score to NULL.")
                
                last_checked_at = None

                file_path1 = None
                file_path2 = None # To remain empty
                file_url = None

                if not pd.isna(file_location_excel):
                    file_location_str = str(file_location_excel).strip()
                    if is_url(file_location_str):
                        file_url = file_location_str
                    else:
                        file_path1 = transform_windows_to_linux_path(file_location_str)
                
                if not (file_path1 or file_path2 or file_url):
                    print(f"Warning: Row {index + 2} in Excel has no valid file_path/URL from column E ('{file_location_excel}'). Skipping file location for MV '{title}'.")

                # --- 2. Insert into new 'music_videos' table ---
                cur_new.execute("""
                    INSERT INTO music_videos (title, release_date, file_path1, file_path2, file_url, score, last_checked_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (title, release_date, file_path1, file_path2, file_url, score, last_checked_at))
                
                new_mv_id = cur_new.lastrowid
                migrated_count += 1

                # --- 3. Get new artist_id from new 'artists' table ---
                if not pd.isna(group_name_excel):
                    artist_name_to_find = str(group_name_excel).strip()
                    cur_new.execute("SELECT artist_id FROM artists WHERE artist_name = ?", (artist_name_to_find,))
                    artist_row_new = cur_new.fetchone()

                    if not artist_row_new:
                        warning_msg = f"Excel Row {index + 2}: Could not find artist_id for artist_name '{artist_name_to_find}' (from Excel Column B) in new DB. Skipping artist link for MV '{title}'."
                        print(f"Error: {warning_msg}")
                        skipped_artist_not_found.append(f"Excel Row {index + 2} (Artist: {artist_name_to_find}, MV Title: {title})")
                        error_count +=1
                        # MV is already inserted, just the link is skipped.
                    else:
                        new_artist_id = artist_row_new[0]
                        # --- 4. Insert into 'music_video_artist_link' ---
                        cur_new.execute("""
                            INSERT INTO music_video_artist_link (mv_id, artist_id)
                            VALUES (?, ?)
                        """, (new_mv_id, new_artist_id))
                        link_count +=1
                else:
                    print(f"Warning: Row {index + 2} in Excel has no group name (Column B). MV '{title}' inserted without an artist link.")

            except sqlite3.IntegrityError as e:
                print(f"IntegrityError for Excel row {index + 2} (MV Title: {title_excel}): {e}. Skipping this record.")
                error_count += 1
            except Exception as e:
                print(f"An unexpected error occurred for Excel row {index + 2} (MV Title: {title_excel}): {e}. Skipping this record.")
                error_count += 1
                import traceback
                traceback.print_exc()


        conn_new.commit()
        print("\n--- Music Video Migration Summary (Pandas) ---")
        print(f"Successfully migrated {migrated_count} music video records.")
        print(f"Successfully created {link_count} music video-artist links.")
        print(f"Encountered {error_count} errors/skipped records during processing.")
        if skipped_artist_not_found:
            print("\n--- Artists Not Found (Skipped Links) ---")
            for item in skipped_artist_not_found:
                print(item)

    except Exception as e:
        print(f"An overall error occurred: {e}")
        import traceback
        traceback.print_exc()
        if conn_new:
            conn_new.rollback()
    finally:
        if conn_new:
            conn_new.close()
        print("Database connection closed (if opened).")

if __name__ == '__main__':
    migrate_music_videos_pandas()
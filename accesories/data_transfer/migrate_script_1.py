import sqlite3
import os

# --- Configuration ---
OLD_DB_PATH = './kpop_database.db'
NEW_DB_PATH = './KpopDatabase_new.db'

# --- Helper function to identify URLs ---
def is_url(path_string):
    if path_string is None:
        return False
    path_string_lower = path_string.lower()
    return path_string_lower.startswith('http://') or \
           path_string_lower.startswith('https://') or \
           path_string_lower.startswith('www.') # Add other common URL prefixes if needed

def migrate_performances():
    if not os.path.exists(OLD_DB_PATH):
        print(f"Error: Old database '{OLD_DB_PATH}' not found.")
        return
    if not os.path.exists(NEW_DB_PATH):
        print(f"Error: New database '{NEW_DB_PATH}' not found.")
        return

    conn_old = None
    conn_new = None

    try:
        # Connect to the databases
        conn_old = sqlite3.connect(OLD_DB_PATH)
        conn_old.row_factory = sqlite3.Row # Access columns by name
        cur_old = conn_old.cursor()

        conn_new = sqlite3.connect(NEW_DB_PATH)
        cur_new = conn_new.cursor()

        print("Fetching performances from old database...")
        cur_old.execute("SELECT performance_id, group_id, performance_date, show_type, resolution, file_path, score, notes FROM performances")
        old_performances = cur_old.fetchall()
        print(f"Found {len(old_performances)} performances to migrate.")

        migrated_count = 0
        link_count = 0
        error_count = 0

        for old_perf in old_performances:
            try:
                # 1. Prepare data for new 'performances' table
                title = old_perf['notes']
                performance_date = old_perf['performance_date']
                show_type = old_perf['show_type']
                resolution = old_perf['resolution']
                score = old_perf['score']
                last_checked_at = None # As requested

                old_file_path_val = old_perf['file_path']
                file_path1 = None
                file_path2 = None # To remain empty
                file_url = None

                if old_file_path_val:
                    if is_url(old_file_path_val):
                        file_url = old_file_path_val
                    else:
                        file_path1 = old_file_path_val
                
                # Check constraint: at least one location must be non-null
                if not (file_path1 or file_path2 or file_url):
                    print(f"Warning: Performance ID {old_perf['performance_id']} (old DB) has no valid file_path/URL '{old_file_path_val}'. Skipping file location, but this might violate a CHECK constraint if all are NULL.")
                    # If your CHECK constraint `chk_performance_location` requires one,
                    # you might need to decide how to handle this (e.g., skip the record or assign a placeholder if permissible)

                # 2. Insert into new 'performances' table
                cur_new.execute("""
                    INSERT INTO performances (title, performance_date, show_type, resolution, file_path1, file_path2, file_url, score, last_checked_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (title, performance_date, show_type, resolution, file_path1, file_path2, file_url, score, last_checked_at))
                
                new_performance_id = cur_new.lastrowid
                migrated_count += 1

                # 3. Get group_name from old 'groups' table
                cur_old.execute("SELECT group_name FROM groups WHERE group_id = ?", (old_perf['group_id'],))
                group_row = cur_old.fetchone()
                if not group_row:
                    print(f"Error: Could not find group_name for group_id {old_perf['group_id']} (old DB performance_id: {old_perf['performance_id']}). Skipping artist link.")
                    error_count += 1
                    continue
                
                artist_name_from_old_group = group_row['group_name']

                # 4. Get new artist_id from new 'artists' table
                cur_new.execute("SELECT artist_id FROM artists WHERE artist_name = ?", (artist_name_from_old_group,))
                artist_row_new = cur_new.fetchone()
                if not artist_row_new:
                    print(f"Error: Could not find artist_id for artist_name '{artist_name_from_old_group}' in new DB (derived from old DB performance_id: {old_perf['performance_id']}). Skipping artist link.")
                    error_count += 1
                    continue
                
                new_artist_id = artist_row_new[0] # artist_id is the first column

                # 5. Insert into 'performance_artist_link'
                # artist_order will take its DEFAULT value (1) as it's not specified
                cur_new.execute("""
                    INSERT INTO performance_artist_link (performance_id, artist_id)
                    VALUES (?, ?)
                """, (new_performance_id, new_artist_id))
                link_count +=1

            except sqlite3.IntegrityError as e:
                print(f"IntegrityError for old performance_id {old_perf['performance_id']}: {e}. Skipping this record.")
                error_count += 1
            except Exception as e:
                print(f"An unexpected error occurred for old performance_id {old_perf['performance_id']}: {e}. Skipping this record.")
                error_count += 1
                # For debugging, you might want to re-raise the exception or log more details
                # import traceback
                # traceback.print_exc()

        # Commit changes to the new database
        conn_new.commit()
        print("\n--- Migration Summary ---")
        print(f"Successfully migrated {migrated_count} performance records.")
        print(f"Successfully created {link_count} performance-artist links.")
        print(f"Encountered {error_count} errors/skipped records.")

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        if conn_new:
            conn_new.rollback() # Rollback any partial changes on error
    finally:
        if conn_old:
            conn_old.close()
        if conn_new:
            conn_new.close()
        print("Database connections closed.")

if __name__ == '__main__':
    migrate_performances()
import sqlite3
import pandas as pd

DATABASE_FILE = "kpop_music.db"
OUTPUT_CSV_PERFORMANCES = "performances_for_song_extraction.csv" # For me to process

def export_performances_for_song_extraction(db_file, output_csv):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        print("Connected to database.")
        # Select performances, especially those where notes might be missing or need parsing
        # You can add a WHERE clause if you only want to process certain ones, e.g., WHERE notes IS NULL OR notes = ''
        query = "SELECT performance_id, file_path, notes FROM performances ORDER BY performance_id;"
        df = pd.read_sql_query(query, conn)
        df.to_csv(output_csv, index=False, encoding='utf-8')
        print(f"Exported {len(df)} rows to {output_csv}")
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    export_performances_for_song_extraction(DATABASE_FILE, OUTPUT_CSV_PERFORMANCES)
CREATE TABLE IF NOT EXISTS groups (
        group_id INTEGER PRIMARY KEY,
        group_name TEXT NOT NULL UNIQUE,
        group_profile TEXT,
        picture_path TEXT
);
CREATE TABLE IF NOT EXISTS members (
        member_id INTEGER PRIMARY KEY,
        group_id INTEGER NOT NULL,
        member_name TEXT NOT NULL,
        picture_path TEXT,
        FOREIGN KEY (group_id) REFERENCES groups (group_id)
);
CREATE TABLE IF NOT EXISTS songs (
        song_id INTEGER PRIMARY KEY,
        song_title TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS performances (
        performance_id INTEGER PRIMARY KEY,
        group_id INTEGER NOT NULL, -- Must link to a group
        performance_date TEXT NOT NULL, -- Assume date always exists
        show_type TEXT, -- Allow missing show type
        resolution TEXT, -- Allow missing resolution
        file_path TEXT NOT NULL UNIQUE, -- UBUNTU path, assume unique & required
        score INTEGER, -- Allow missing score
        notes TEXT, -- Allow missing notes (maybe replace with song_title_raw?)
        FOREIGN KEY (group_id) REFERENCES groups (group_id)
); 
# Note: We might add a 'song_title_raw' column here later if needed before song linking

CREATE TABLE IF NOT EXISTS performance_songs (
        performance_id INTEGER NOT NULL,
        song_id INTEGER NOT NULL,
        FOREIGN KEY (performance_id) REFERENCES performances (performance_id),
        FOREIGN KEY (song_id) REFERENCES songs (song_id),
        PRIMARY KEY (performance_id, song_id) -- Composite PK
);
CREATE TABLE IF NOT EXISTS music_videos (
        mv_id INTEGER PRIMARY KEY,
        group_id INTEGER NOT NULL,
        song_id INTEGER,
        release_date TEXT NOT NULL,
        file_path TEXT NOT NULL UNIQUE, -- Assume unique & required
        score INTEGER, -- Allow missing score
        title TEXT NOT NULL, -- Assuming MV title is important
        FOREIGN KEY (group_id) REFERENCES groups (group_id),
        FOREIGN KEY (song_id) REFERENCES songs (song_id)
);
CREATE TABLE IF NOT EXISTS fancams (
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
);

import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import webbrowser
import datetime
from tkinter import simpledialog
import os

import db_operations
import utils
import config

# UI theme constants
DARK_BG = "#222222"
BRIGHT_FG = "#f8f8f2"
ACCENT = "#44475a"
FONT_MAIN = ("Courier New", 13)
FONT_HEADER = ("Courier New", 13, "bold")
FONT_LABEL_SMALL = ("Courier New", 11)
FONT_BUTTON = ("Arial", 13, "bold")

class ModifyEntryWindow(tk.Toplevel):
    """
    Window for modifying or deleting an existing performance or MV record.
    """
    def __init__(self, master, record, refresh_callback):
        super().__init__(master)
        self.record = record
        self.refresh_callback = refresh_callback
        # Set window title to include the entry's current title
        entry_title = self.record.get('db_title', '') or self.record.get('db_title', '')
        self.title(f"Modify Entry - {entry_title}")
        self.configure(bg=DARK_BG)
        self.transient(master)
        self.grab_set()

        # Build form fields
        form_frame = ttk.Frame(self, padding=20)
        form_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        ttk.Label(form_frame, text="Title:", background=DARK_BG, foreground=BRIGHT_FG, font=FONT_MAIN).grid(row=0, column=0, sticky="w", pady=2)
        self.title_var = tk.StringVar(value=self.record.get("db_title", ""))
        ttk.Entry(form_frame, textvariable=self.title_var, width=50, font=FONT_MAIN).grid(row=0, column=1, sticky="w", pady=2)

        # Date
        ttk.Label(form_frame, text="Date (YYYY-MM-DD):", background=DARK_BG, foreground=BRIGHT_FG, font=FONT_MAIN).grid(row=1, column=0, sticky="w", pady=2)
        self.date_var = tk.StringVar(value=self.record.get("performance_date", ""))
        ttk.Entry(form_frame, textvariable=self.date_var, width=20, font=FONT_MAIN).grid(row=1, column=1, sticky="w", pady=2)

        # Load choices for show type and resolution from DB
        try:
            conn = db_operations.get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT show_type FROM performances WHERE show_type IS NOT NULL AND TRIM(show_type)!='' ORDER BY show_type;")
            self.show_type_choices = [row[0] for row in cur.fetchall() if row[0]]
            cur.execute("SELECT DISTINCT resolution FROM performances WHERE resolution IS NOT NULL AND TRIM(resolution)!='' ORDER BY resolution;")
            self.resolution_choices = [row[0] for row in cur.fetchall() if row[0]]
        except Exception:
            self.show_type_choices = []
            self.resolution_choices = []
        # Show Type
        ttk.Label(form_frame, text="Show Type:", background=DARK_BG, foreground=BRIGHT_FG, font=FONT_MAIN).grid(row=2, column=0, sticky="w", pady=2)
        self.show_type_var = tk.StringVar(value=self.record.get("show_type", ""))
        showtype_combo = ttk.Combobox(form_frame, textvariable=self.show_type_var,
            values=(self.show_type_choices + ["<Add new>"] if self.show_type_choices else ["<Add new>"]),
            state="readonly", width=30)
        showtype_combo.grid(row=2, column=1, sticky="w", pady=2)
        def on_showtype_select(event=None):
            if self.show_type_var.get() == "<Add new>":
                new_val = simpledialog.askstring("Add Show Type", "Enter new show type:", parent=self)
                if new_val:
                    if new_val not in self.show_type_choices:
                        self.show_type_choices.append(new_val)
                        self.show_type_choices.sort(key=lambda s: s.lower())
                    showtype_combo['values'] = self.show_type_choices + ["<Add new>"]
                    self.show_type_var.set(new_val)
        showtype_combo.bind("<<ComboboxSelected>>", on_showtype_select)

        # Resolution
        ttk.Label(form_frame, text="Resolution:", background=DARK_BG, foreground=BRIGHT_FG, font=FONT_MAIN).grid(row=3, column=0, sticky="w", pady=2)
        self.resolution_var = tk.StringVar(value=self.record.get("resolution", ""))
        res_combo = ttk.Combobox(form_frame, textvariable=self.resolution_var,
            values=(self.resolution_choices + ["<Add new>"] if self.resolution_choices else ["<Add new>"]),
            state="readonly", width=20)
        res_combo.grid(row=3, column=1, sticky="w", pady=2)
        def on_res_select(event=None):
            if self.resolution_var.get() == "<Add new>":
                new_val = simpledialog.askstring("Add Resolution", "Enter new resolution:", parent=self)
                if new_val:
                    if new_val not in self.resolution_choices:
                        self.resolution_choices.append(new_val)
                        self.resolution_choices.sort(key=lambda s: s.lower())
                    res_combo['values'] = self.resolution_choices + ["<Add new>"]
                    self.resolution_var.set(new_val)
        res_combo.bind("<<ComboboxSelected>>", on_res_select)

        # File Path1
        ttk.Label(form_frame, text="File Path1:", background=DARK_BG, foreground=BRIGHT_FG, font=FONT_MAIN).grid(row=4, column=0, sticky="w", pady=2)
        self.file_path1_var = tk.StringVar(value=self.record.get("file_path1", "") or "")
        ttk.Entry(form_frame, textvariable=self.file_path1_var, width=60, state='readonly', font=FONT_MAIN).grid(row=4, column=1, sticky="w", pady=2)

        # File Path2
        ttk.Label(form_frame, text="File Path2:", background=DARK_BG, foreground=BRIGHT_FG, font=FONT_MAIN).grid(row=5, column=0, sticky="w", pady=2)
        self.file_path2_var = tk.StringVar(value=self.record.get("file_path2", "") or "")
        ttk.Entry(form_frame, textvariable=self.file_path2_var, width=60, state='readonly', font=FONT_MAIN).grid(row=5, column=1, sticky="w", pady=2)

        # URL
        ttk.Label(form_frame, text="URL:", background=DARK_BG, foreground=BRIGHT_FG, font=FONT_MAIN).grid(row=6, column=0, sticky="w", pady=2)
        self.file_url_var = tk.StringVar(value=self.record.get("file_url", "") or "")
        ttk.Entry(form_frame, textvariable=self.file_url_var, width=60, state='readonly', font=FONT_MAIN).grid(row=6, column=1, sticky="w", pady=2)

        # Score
        ttk.Label(form_frame, text="Score:", background=DARK_BG, foreground=BRIGHT_FG, font=FONT_MAIN).grid(row=7, column=0, sticky="w", pady=2)
        self.score_var = tk.IntVar(value=self.record.get("score") or 0)
        ttk.Spinbox(form_frame, from_=0, to=5, textvariable=self.score_var, width=5).grid(row=7, column=1, sticky="w", pady=2)

        # Primary Artist
        artists_list = [a['name'] for a in db_operations.get_all_artists()]
        primary, *rest = [s.strip() for s in self.record.get("artists_str", "").split(',')]
        secondary = rest[0] if rest else ""
        ttk.Label(form_frame, text="Primary Artist:", background=DARK_BG, foreground=BRIGHT_FG, font=FONT_MAIN).grid(row=8, column=0, sticky="w", pady=2)
        self.primary_artist_var = tk.StringVar(value=primary)
        ttk.Entry(form_frame, textvariable=self.primary_artist_var, width=30, state='readonly', font=FONT_MAIN).grid(row=8, column=1, sticky="w", pady=2)
        ttk.Button(form_frame, text="Select...", command=self.show_artist_listbox_popup).grid(row=8, column=2, sticky="w", padx=5)
        # Secondary Artist
        ttk.Label(form_frame, text="Secondary Artist:", background=DARK_BG, foreground=BRIGHT_FG, font=FONT_MAIN).grid(row=9, column=0, sticky="w", pady=2)
        self.secondary_artist_var = tk.StringVar(value=secondary)
        ttk.Entry(form_frame, textvariable=self.secondary_artist_var, width=30, state='readonly', font=FONT_MAIN).grid(row=9, column=1, sticky="w", pady=2)
        ttk.Button(form_frame, text="Select...", command=self.show_secondary_artist_listbox_popup).grid(row=9, column=2, sticky="w", padx=5)

        # Songs
        ttk.Label(form_frame, text="Songs (comma-separated):", background=DARK_BG, foreground=BRIGHT_FG, font=FONT_MAIN).grid(row=10, column=0, sticky="w", pady=2)
        self.songs_var = tk.StringVar(value=self.record.get("songs_str", ""))
        ttk.Entry(form_frame, textvariable=self.songs_var, width=60, font=FONT_MAIN).grid(row=10, column=1, sticky="w", pady=2)
        ttk.Button(form_frame, text="Select Song(s)", command=self.show_song_selection_popup).grid(row=10, column=2, sticky="w", padx=5)

        # Buttons
        btn_frame = ttk.Frame(self, style="TFrame")
        btn_frame.pack(fill=tk.X, pady=10)
        # Play button to preview media before saving
        ttk.Button(btn_frame, text="Play", command=self.play_current_entry, style="TButton").pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Save", command=self.save_modified_entry, style="TButton").pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Delete", command=self.delete_entry, style="TButton").pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.cancel, style="TButton").pack(side=tk.RIGHT, padx=5)

        # Load show type and resolution choices from DB
        try:
            conn = db_operations.get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT show_type FROM performances WHERE show_type IS NOT NULL AND TRIM(show_type)!='' ORDER BY show_type;")
            self.show_type_choices = [row[0] for row in cur.fetchall() if row[0]]
            
            # Load resolution choices from both performances and music_videos tables
            resolution_set = set()
            cur.execute("SELECT DISTINCT resolution FROM performances WHERE resolution IS NOT NULL AND TRIM(resolution)!='' ORDER BY resolution;")
            resolution_set.update(row[0] for row in cur.fetchall() if row[0])
            cur.execute("SELECT DISTINCT resolution FROM music_videos WHERE resolution IS NOT NULL AND TRIM(resolution)!='' ORDER BY resolution;")
            resolution_set.update(row[0] for row in cur.fetchall() if row[0])
            
            self.resolution_choices = sorted(list(resolution_set), key=lambda s: s.lower())
        except Exception:
            self.show_type_choices = []
            self.resolution_choices = []

        # Disable Show Type for music video entries (but enable Resolution)
        entry_type = self.record.get('entry_type', 'performance')
        if entry_type != 'performance':
            showtype_combo.config(state='disabled')
            # Keep resolution enabled for music videos

    def save_modified_entry(self):
        # Gather values
        entry_type = self.record.get('entry_type', 'performance')
        title = self.title_var.get().strip()
        date = self.date_var.get().strip()
        file_path1 = self.file_path1_var.get().strip() or None
        file_path2 = self.file_path2_var.get().strip() or None
        file_url = self.file_url_var.get().strip() or None
        score = self.score_var.get()
        primary_artist = self.primary_artist_var.get().strip()
        secondary_artist = self.secondary_artist_var.get().strip()
        artists = [primary_artist]
        if secondary_artist and secondary_artist != primary_artist:
            artists.append(secondary_artist)
        songs = [s.strip() for s in self.songs_var.get().split(',') if s.strip()]
        # Validate date format YYYY-MM-DD
        try:
            datetime.datetime.strptime(date, "%Y-%m-%d")
        except Exception:
            messagebox.showerror("Invalid Date", "Date must be in YYYY-MM-DD format.", parent=self)
            return
        try:
            if entry_type == 'performance':
                show_type = self.show_type_var.get().strip()
                resolution = self.resolution_var.get().strip()
                perf_id = self.record.get('performance_id')
                db_operations.update_performance(
                    perf_id, title, date, show_type, resolution,
                    file_path1, file_path2, file_url, score,
                    artists, songs
                )
                messagebox.showinfo("Success", "Performance updated successfully.", parent=self)
            else:
                resolution = self.resolution_var.get().strip()
                mv_id_raw = self.record.get('performance_id')
                mv_id = int(mv_id_raw.split('_',1)[1]) if isinstance(mv_id_raw, str) and mv_id_raw.startswith('mv_') else mv_id_raw
                db_operations.update_music_video(
                    mv_id, title, date, resolution,
                    file_path1, file_path2, file_url, score,
                    artists, songs
                )
                messagebox.showinfo("Success", "Music video updated successfully.", parent=self)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update entry: {e}", parent=self)
            return
        # Refresh and close
        if self.refresh_callback:
            self.refresh_callback()
        self.destroy()

    def delete_entry(self):
        # Confirm deletion
        if not messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this entry?", parent=self):
            return
        entry_type = self.record.get('entry_type', 'performance')
        try:
            if entry_type == 'performance':
                perf_id = self.record.get('performance_id')
                db_operations.delete_performance(perf_id)
            else:
                mv_id_raw = self.record.get('performance_id')
                mv_id = int(mv_id_raw.split('_',1)[1]) if isinstance(mv_id_raw, str) and mv_id_raw.startswith('mv_') else mv_id_raw
                db_operations.delete_music_video(mv_id)
            messagebox.showinfo("Deleted", "Entry deleted successfully.", parent=self)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete entry: {e}", parent=self)
            return
        # Prompt to delete associated local file(s)
        local_paths = [self.record.get('file_path1'), self.record.get('file_path2')]
        local_paths = [p for p in local_paths if p]
        if local_paths:
            files_list = '\n'.join(local_paths)
            if messagebox.askyesno("Delete File(s)", f"Do you also want to delete these local file(s)?\n{files_list}", parent=self):
                for path in local_paths:
                    # Only attempt to delete if file exists
                    if not os.path.exists(path):
                        continue
                    try:
                        os.remove(path)
                    except Exception as err:
                        messagebox.showerror("File Delete Error", f"Failed to delete '{path}': {err}", parent=self)
        # Refresh and close
        if self.refresh_callback:
            self.refresh_callback()
        self.destroy()
    
    def play_current_entry(self):
        """Plays the current record's media for preview."""
        path, is_yt = utils.get_playable_path_info(self.record)
        if not path:
            messagebox.showerror("Play Error", "No media path or URL available to play.", parent=self)
            return
        try:
            if is_yt:
                webbrowser.open_new_tab(path)
            else:
                subprocess.Popen([config.MPV_PLAYER_PATH, path])
        except Exception as e:
            messagebox.showerror("Play Error", f"Failed to play media: {e}", parent=self)

    def cancel(self):
        # Close without saving
        self.destroy()

    def show_artist_listbox_popup(self):
        """Show a popup to select an artist from the list."""
        popup = ArtistSelectPopup(self, "Select Primary Artist", self.primary_artist_var.get(), self.update_primary_artist)
        self.wait_window(popup)

    def show_secondary_artist_listbox_popup(self):
        """Show a popup to select a secondary artist from the list."""
        popup = ArtistSelectPopup(self, "Select Secondary Artist", self.secondary_artist_var.get(), self.update_secondary_artist)
        self.wait_window(popup)

    def update_primary_artist(self, artist_name):
        """Update the primary artist field."""
        self.primary_artist_var.set(artist_name)

    def update_secondary_artist(self, artist_name):
        """Update the secondary artist field."""
        self.secondary_artist_var.set(artist_name)

    def get_songs_for_selected_artists(self):
        # Reuse DataEntryWindow logic for fetching songs
        artists = [self.primary_artist_var.get()]
        if self.secondary_artist_var.get().strip():
            artists.append(self.secondary_artist_var.get())
        # Fetch all songs linked to these artists, mimic DataEntryWindow
        conn = db_operations.get_db_connection()
        song_rows = []
        if artists:
            placeholders = ",".join("?" for _ in artists)
            # artist_ids
            artist_ids = []
            for name in artists:
                cursor = conn.cursor()
                cursor.execute("SELECT artist_id FROM artists WHERE artist_name = ?", (name,))
                row = cursor.fetchone()
                if row:
                    artist_ids.append(row[0])
            if artist_ids:
                ph_art = ",".join("?" for _ in artist_ids)
                query = f"SELECT DISTINCT s.song_id, s.song_title FROM songs s JOIN song_artist_link sal ON s.song_id=sal.song_id WHERE sal.artist_id IN ({ph_art}) ORDER BY s.song_title COLLATE NOCASE"
                cursor.execute(query, artist_ids)
                song_rows = cursor.fetchall()
        return song_rows

    def show_song_selection_popup(self):
        songs = self.get_songs_for_selected_artists()
        if not songs:
            messagebox.showinfo("No Songs", "No songs found for the selected artist(s).", parent=self)
            return
        # Map titles to song_ids
        title_to_ids = {}
        for sid, title in songs:
            title_to_ids.setdefault(title, []).append(sid)
        titles = sorted(title_to_ids.keys(), key=lambda t: t.lower())
        popup = tk.Toplevel(self)
        popup.title("Select Song(s)")
        popup.configure(bg=DARK_BG)
        popup.geometry("400x500+%d+%d" % (self.winfo_rootx()+140, self.winfo_rooty()+140))
        popup.transient(self)
        popup.grab_set()
        frame = tk.Frame(popup, bg=DARK_BG)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        scrollbar = tk.Scrollbar(frame, orient="vertical")
        listbox = tk.Listbox(frame, selectmode=tk.MULTIPLE, bg="#333a40", fg=BRIGHT_FG, font=FONT_MAIN, yscrollcommand=scrollbar.set)
        scrollbar.config(command=listbox.yview)
        scrollbar.pack(side="right", fill="y")
        listbox.pack(side="left", fill="both", expand=True)
        for t in titles:
            listbox.insert(tk.END, t)
        # Pre-select current songs
        old_songs = [s.strip() for s in self.songs_var.get().split(',') if s.strip()]
        if old_songs:
            if messagebox.askyesno("Delete Previous Songs", "Previous songs exist. Do you want to delete them?", parent=self):
                old_songs = []
                self.songs_var.set("")
        for idx, t in enumerate(titles):
            if t in old_songs:
                listbox.selection_set(idx)
        def on_ok():
            selected = [titles[i] for i in listbox.curselection()]
            new_songs = selected
            new_songs_str = ', '.join(new_songs)
            self.songs_var.set(new_songs_str)
            # If songs changed, update title and warn on top of popup
            if set(old_songs) != set(new_songs):
                self.title_var.set(new_songs_str)
                messagebox.showwarning(
                    "Title Updated",
                    f"Title has been set to the selected songs: {new_songs_str}. Please modify manually if needed.",
                    parent=popup
                )
            popup.destroy()
        btn_frame = ttk.Frame(popup, padding=10)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text="OK", command=on_ok, style="TButton").pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=popup.destroy, style="TButton").pack(side=tk.RIGHT, padx=5)

    def update_song_list(self, filtered_songs=None):
        """Update the listbox with the song names."""
        self.song_listbox.delete(0, tk.END)
        for song in (filtered_songs or self.song_list):
            self.song_listbox.insert(tk.END, song['title'])
        # Select the currently assigned songs
        for i in range(self.song_listbox.size()):
            song_title = self.song_listbox.get(i)
            if song_title in self.selected_songs:
                self.song_listbox.select_set(i)

    def filter_song_list(self, *args):
        """Filter the song list based on the search query."""
        query = self.search_var.get().strip().lower()
        filtered_songs = [song for song in self.song_list if query in song['title'].lower()]
        self.update_song_list(filtered_songs)

    def on_song_select(self, event=None):
        """Handle song selection from the list."""
        selected = self.song_listbox.curselection()
        if selected:
            song_titles = [self.song_listbox.get(i) for i in selected]
            self.callback(song_titles)
            self.destroy()

    def on_ok(self):
        """Handle OK button click."""
        self.on_song_select()

class ArtistSelectPopup(tk.Toplevel):
    """
    Popup window for selecting an artist from the list.
    """
    def __init__(self, parent, title, selected_artist, callback):
        super().__init__(parent)
        self.title(title)
        self.parent = parent
        self.callback = callback
        self.artist_list = db_operations.get_all_artists()
        self.selected_artist = selected_artist

        # Search variable
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self.filter_artist_list)

        # Build UI
        self.geometry("400x300")
        self.configure(bg=DARK_BG)

        # Search box
        search_frame = ttk.Frame(self, padding=10)
        search_frame.pack(fill=tk.X)
        ttk.Label(search_frame, text="Search:", background=DARK_BG, foreground=BRIGHT_FG).pack(side=tk.LEFT, padx=5)
        ttk.Entry(search_frame, textvariable=self.search_var, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # Artist listbox
        self.artist_listbox = tk.Listbox(self, selectmode=tk.SINGLE, bg=DARK_BG, fg=BRIGHT_FG, font=FONT_MAIN)
        self.artist_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.artist_listbox.bind("<Double-Button-1>", self.on_artist_select)

        # Buttons
        btn_frame = ttk.Frame(self, padding=10)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text="OK", command=self.on_ok, style="TButton").pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy, style="TButton").pack(side=tk.RIGHT, padx=5)

        # Initialize artist list
        self.update_artist_list()

    def update_artist_list(self, filtered_artists=None):
        """Update the listbox with the artist names."""
        self.artist_listbox.delete(0, tk.END)
        for artist in (filtered_artists or self.artist_list):
            self.artist_listbox.insert(tk.END, artist['name'])
        # Select the current artist
        if self.selected_artist:
            try:
                index = next(i for i, artist in enumerate(self.artist_list) if artist['name'] == self.selected_artist)
                self.artist_listbox.select_set(index)
                self.artist_listbox.see(index)
            except StopIteration:
                pass  # Current artist not in list, do not select any

    def filter_artist_list(self, *args):
        """Filter the artist list based on the search query."""
        query = self.search_var.get().strip().lower()
        filtered_artists = [artist for artist in self.artist_list if query in artist['name'].lower()]
        self.update_artist_list(filtered_artists)

    def on_artist_select(self, event=None):
        """Handle artist selection from the list."""
        selected = self.artist_listbox.curselection()
        if selected:
            artist_name = self.artist_listbox.get(selected)
            self.callback(artist_name)
            self.destroy()

    def on_ok(self):
        """Handle OK button click."""
        self.on_artist_select()

class SongSelectPopup(tk.Toplevel):
    """
    Popup window for selecting songs from the list.
    """
    def __init__(self, parent, title, selected_songs, callback):
        super().__init__(parent)
        self.title(title)
        self.parent = parent
        self.callback = callback
        self.song_list = db_operations.get_all_songs()
        self.selected_songs = set(selected_songs)  # Use a set for faster lookup

        # Search variable
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self.filter_song_list)

        # Build UI
        self.geometry("450x350")
        self.configure(bg=DARK_BG)

        # Search box
        search_frame = ttk.Frame(self, padding=10)
        search_frame.pack(fill=tk.X)
        ttk.Label(search_frame, text="Search:", background=DARK_BG, foreground=BRIGHT_FG).pack(side=tk.LEFT, padx=5)
        ttk.Entry(search_frame, textvariable=self.search_var, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # Song listbox
        self.song_listbox = tk.Listbox(self, selectmode=tk.MULTIPLE, bg=DARK_BG, fg=BRIGHT_FG, font=FONT_MAIN)
        self.song_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.song_listbox.bind("<Double-Button-1>", self.on_song_select)

        # Buttons
        btn_frame = ttk.Frame(self, padding=10)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text="OK", command=self.on_ok, style="TButton").pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy, style="TButton").pack(side=tk.RIGHT, padx=5)

        # Initialize song list
        self.update_song_list()

    def update_song_list(self, filtered_songs=None):
        """Update the listbox with the song names."""
        self.song_listbox.delete(0, tk.END)
        for song in (filtered_songs or self.song_list):
            self.song_listbox.insert(tk.END, song['title'])
        # Select the currently assigned songs
        for i in range(self.song_listbox.size()):
            song_title = self.song_listbox.get(i)
            if song_title in self.selected_songs:
                self.song_listbox.select_set(i)

    def filter_song_list(self, *args):
        """Filter the song list based on the search query."""
        query = self.search_var.get().strip().lower()
        filtered_songs = [song for song in self.song_list if query in song['title'].lower()]
        self.update_song_list(filtered_songs)

    def on_song_select(self, event=None):
        """Handle song selection from the list."""
        selected = self.song_listbox.curselection()
        if selected:
            song_titles = [self.song_listbox.get(i) for i in selected]
            self.callback(song_titles)
            self.destroy()

    def on_ok(self):
        """Handle OK button click."""
        self.on_song_select()

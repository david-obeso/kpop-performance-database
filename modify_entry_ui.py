import tkinter as tk
from tkinter import ttk, messagebox

import db_operations
import utils
import subprocess
import webbrowser
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
        self.title("Modify Entry")
        self.configure(bg=DARK_BG)
        self.transient(master)
        self.grab_set()

        # Build form fields
        form_frame = ttk.Frame(self, padding=20)
        form_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        ttk.Label(form_frame, text="Title:", background=DARK_BG, foreground=BRIGHT_FG, font=FONT_MAIN).grid(row=0, column=0, sticky="w", pady=2)
        self.title_var = tk.StringVar(value=self.record.get("db_title", ""))
        ttk.Entry(form_frame, textvariable=self.title_var, width=50).grid(row=0, column=1, sticky="w", pady=2)

        # Date
        ttk.Label(form_frame, text="Date (YYYY-MM-DD):", background=DARK_BG, foreground=BRIGHT_FG, font=FONT_MAIN).grid(row=1, column=0, sticky="w", pady=2)
        self.date_var = tk.StringVar(value=self.record.get("performance_date", ""))
        ttk.Entry(form_frame, textvariable=self.date_var, width=20).grid(row=1, column=1, sticky="w", pady=2)

        # Show Type
        ttk.Label(form_frame, text="Show Type:", background=DARK_BG, foreground=BRIGHT_FG, font=FONT_MAIN).grid(row=2, column=0, sticky="w", pady=2)
        self.show_type_var = tk.StringVar(value=self.record.get("show_type", ""))
        ttk.Entry(form_frame, textvariable=self.show_type_var, width=30).grid(row=2, column=1, sticky="w", pady=2)

        # Resolution
        ttk.Label(form_frame, text="Resolution:", background=DARK_BG, foreground=BRIGHT_FG, font=FONT_MAIN).grid(row=3, column=0, sticky="w", pady=2)
        self.resolution_var = tk.StringVar(value=self.record.get("resolution", ""))
        ttk.Entry(form_frame, textvariable=self.resolution_var, width=20).grid(row=3, column=1, sticky="w", pady=2)

        # File Path1
        ttk.Label(form_frame, text="File Path1:", background=DARK_BG, foreground=BRIGHT_FG, font=FONT_MAIN).grid(row=4, column=0, sticky="w", pady=2)
        self.file_path1_var = tk.StringVar(value=self.record.get("file_path1", "") or "")
        ttk.Entry(form_frame, textvariable=self.file_path1_var, width=60).grid(row=4, column=1, sticky="w", pady=2)

        # File Path2
        ttk.Label(form_frame, text="File Path2:", background=DARK_BG, foreground=BRIGHT_FG, font=FONT_MAIN).grid(row=5, column=0, sticky="w", pady=2)
        self.file_path2_var = tk.StringVar(value=self.record.get("file_path2", "") or "")
        ttk.Entry(form_frame, textvariable=self.file_path2_var, width=60).grid(row=5, column=1, sticky="w", pady=2)

        # URL
        ttk.Label(form_frame, text="URL:", background=DARK_BG, foreground=BRIGHT_FG, font=FONT_MAIN).grid(row=6, column=0, sticky="w", pady=2)
        self.file_url_var = tk.StringVar(value=self.record.get("file_url", "") or "")
        ttk.Entry(form_frame, textvariable=self.file_url_var, width=60).grid(row=6, column=1, sticky="w", pady=2)

        # Score
        ttk.Label(form_frame, text="Score:", background=DARK_BG, foreground=BRIGHT_FG, font=FONT_MAIN).grid(row=7, column=0, sticky="w", pady=2)
        self.score_var = tk.IntVar(value=self.record.get("score") or 0)
        ttk.Spinbox(form_frame, from_=0, to=5, textvariable=self.score_var, width=5).grid(row=7, column=1, sticky="w", pady=2)

        # Artists
        ttk.Label(form_frame, text="Artists (comma-separated):", background=DARK_BG, foreground=BRIGHT_FG, font=FONT_MAIN).grid(row=8, column=0, sticky="w", pady=2)
        self.artists_var = tk.StringVar(value=self.record.get("artists_str", ""))
        ttk.Entry(form_frame, textvariable=self.artists_var, width=60).grid(row=8, column=1, sticky="w", pady=2)

        # Songs
        ttk.Label(form_frame, text="Songs (comma-separated):", background=DARK_BG, foreground=BRIGHT_FG, font=FONT_MAIN).grid(row=9, column=0, sticky="w", pady=2)
        self.songs_var = tk.StringVar(value=self.record.get("songs_str", ""))
        ttk.Entry(form_frame, textvariable=self.songs_var, width=60).grid(row=9, column=1, sticky="w", pady=2)

        # Buttons
        btn_frame = ttk.Frame(self, style="TFrame")
        btn_frame.pack(fill=tk.X, pady=10)
        # Play button to preview media before saving
        ttk.Button(btn_frame, text="Play", command=self.play_current_entry, style="TButton").pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Save", command=self.save_modified_entry, style="TButton").pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Delete", command=self.delete_entry, style="TButton").pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.cancel, style="TButton").pack(side=tk.RIGHT, padx=5)

    def save_modified_entry(self):
        # Gather values
        entry_type = self.record.get('entry_type', 'performance')
        title = self.title_var.get().strip()
        date = self.date_var.get().strip()
        file_path1 = self.file_path1_var.get().strip() or None
        file_path2 = self.file_path2_var.get().strip() or None
        file_url = self.file_url_var.get().strip() or None
        score = self.score_var.get()
        artists = [a.strip() for a in self.artists_var.get().split(',') if a.strip()]
        songs = [s.strip() for s in self.songs_var.get().split(',') if s.strip()]
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
                mv_id_raw = self.record.get('performance_id')
                mv_id = int(mv_id_raw.split('_',1)[1]) if isinstance(mv_id_raw, str) and mv_id_raw.startswith('mv_') else mv_id_raw
                db_operations.update_music_video(
                    mv_id, title, date,
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

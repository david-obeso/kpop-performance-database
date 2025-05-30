# data_entry_ui.py
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import sys
import os
import webbrowser
import datetime
try:
    from tkcalendar import DateEntry
    HAS_TKCALENDAR = True
except ImportError:
    HAS_TKCALENDAR = False

# Modularized imports (will be needed later if not already passed, e.g. config)
# import config
# import utils
# db_operations will be passed in constructor

# Constants
DARK_BG = "#222222"
BRIGHT_FG = "#f8f8f2"
ACCENT = "#44475a"
FONT_MAIN = ("Courier New", 13)
FONT_HEADER = ("Courier New", 13, "bold")
FONT_BUTTON = ("Arial", 13, "bold")
FONT_ENTRY_DATA_UI = ("Courier New", 13)


class DataEntryWindow(tk.Toplevel):
    def __init__(self, master, db_ops): 
        super().__init__(master)
        self.title("Add or Modify Database Entry")
        self.geometry("900x1000")  # Or adjust as needed
        self.configure(bg=DARK_BG)
        self.transient(master)
        self.grab_set()

        self.master_app = master
        self.db_ops = db_ops 

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("DataEntry.TFrame", background=DARK_BG)
        style.configure("DataEntry.TLabel", background=DARK_BG, foreground=BRIGHT_FG, font=FONT_MAIN)
        style.configure("DataEntry.TRadiobutton", background=DARK_BG, foreground=BRIGHT_FG, font=FONT_MAIN,
                        indicatorrelief=tk.FLAT, indicatormargin=-1, indicatordiameter=15)
        style.map("DataEntry.TRadiobutton",
                  indicatorcolor=[('selected', ACCENT), ('!selected', '#555555')],
                  background=[('active', DARK_BG)])
        style.configure("DataEntry.TButton", background=ACCENT, foreground=BRIGHT_FG, font=FONT_BUTTON)
        style.map("DataEntry.TButton", background=[("active", "#6272a4")])
        style.configure("DataEntry.TEntry", fieldbackground=DARK_BG, foreground=BRIGHT_FG, 
                        insertcolor=BRIGHT_FG, font=FONT_ENTRY_DATA_UI, borderwidth=1, relief=tk.SOLID)
        style.map("DataEntry.TEntry", bordercolor=[('focus', '#6272a4'), ('!focus', ACCENT)])

        self.option_add('*DataEntry.TCombobox*Listbox.background', '#333a40')
        self.option_add('*DataEntry.TCombobox*Listbox.foreground', BRIGHT_FG)
        self.option_add('*DataEntry.TCombobox*Listbox.selectBackground', ACCENT)
        self.option_add('*DataEntry.TCombobox*Listbox.selectForeground', '#f1fa8c')
        self.option_add('*DataEntry.TCombobox*Listbox.font', FONT_MAIN)
        style.configure("DataEntry.TCombobox",
            font=FONT_ENTRY_DATA_UI, 
            selectbackground=DARK_BG, 
            selectforeground=BRIGHT_FG, 
            fieldbackground=DARK_BG,
            foreground=BRIGHT_FG,
            arrowcolor=BRIGHT_FG
        )
        style.map("DataEntry.TCombobox",
            fieldbackground=[('readonly', DARK_BG), ('!readonly', DARK_BG)],
            foreground=[('readonly', BRIGHT_FG), ('!readonly', BRIGHT_FG)],
            arrowcolor=[('readonly', BRIGHT_FG)]
        )

        main_frame = ttk.Frame(self, padding="20", style="DataEntry.TFrame")
        main_frame.pack(fill=tk.BOTH, expand=True)

        self.entry_type_var = tk.StringVar(value="performance")
        self.source_type_var = tk.StringVar(value="url")
        self.title_var = tk.StringVar()

        # Added date variable
        self.date_var = tk.StringVar()
        today = datetime.date.today()
        self.date_var.set(today.strftime("%Y-%m-%d"))

        selection_outer_frame = ttk.Frame(main_frame, style="DataEntry.TFrame")
        selection_outer_frame.pack(pady=0, fill="x")

        type_frame = ttk.LabelFrame(selection_outer_frame, text="1. Select Entry Type", style="DataEntry.TFrame", padding=(10, 5))
        type_frame.pack(pady=5, fill="x")
        ttk.Radiobutton(type_frame, text="Performance", variable=self.entry_type_var,
                        value="performance", style="DataEntry.TRadiobutton", command=self.reset_content_on_selection_change).pack(side=tk.LEFT, padx=10, pady=5)
        ttk.Radiobutton(type_frame, text="Music Video", variable=self.entry_type_var,
                        value="music_video", style="DataEntry.TRadiobutton", command=self.reset_content_on_selection_change).pack(side=tk.LEFT, padx=10, pady=5)

        source_frame = ttk.LabelFrame(selection_outer_frame, text="2. Select Source Type", style="DataEntry.TFrame", padding=(10, 5))
        source_frame.pack(pady=5, fill="x")
        ttk.Radiobutton(source_frame, text="Enter New URL", variable=self.source_type_var,
                        value="url", style="DataEntry.TRadiobutton", command=self.reset_content_on_selection_change).pack(side=tk.LEFT, padx=10, pady=5)
        ttk.Radiobutton(source_frame, text="Process Local File(s)", variable=self.source_type_var,
                        value="local_file", style="DataEntry.TRadiobutton", command=self.reset_content_on_selection_change).pack(side=tk.LEFT, padx=10, pady=5)
        
        self.content_area_frame = ttk.LabelFrame(main_frame, text="3. Enter Details", style="DataEntry.TFrame", padding=(10,10))
        self.content_area_frame.pack(pady=10, fill=tk.BOTH, expand=True)
        
        self.current_content_placeholder_label = ttk.Label(self.content_area_frame, text="Select options above and click 'Proceed / Next Step'.", style="DataEntry.TLabel")
        self.current_content_placeholder_label.pack(padx=10, pady=20, anchor="center")

        self.url_entry_var = tk.StringVar()
        self.primary_artist_var = tk.StringVar()
        self.secondary_artist_var = tk.StringVar()
        self.all_artists_list = [] 
        self.selected_song_ids = []  # List of selected song_id
        self.selected_song_titles = []  # Parallel list of song titles for display

        button_frame = ttk.Frame(main_frame, style="DataEntry.TFrame")
        button_frame.pack(fill="x", pady=(10, 0), side=tk.BOTTOM)

        self.proceed_button = ttk.Button(button_frame, text="Proceed / Next Step", command=self.handle_proceed, style="DataEntry.TButton")
        self.proceed_button.pack(side=tk.RIGHT, padx=5)

        self.cancel_button = ttk.Button(button_frame, text="Cancel", command=self.close_window, style="DataEntry.TButton")
        self.cancel_button.pack(side=tk.RIGHT, padx=5)
        
        self.protocol("WM_DELETE_WINDOW", self.close_window)
        self.load_initial_data() 
        self.focus_set()

        self.url_entry_var.trace_add("write", self.on_url_change)

    def load_initial_data(self):
        self.all_artists_list = self.db_ops.get_all_artists()
        # Sort the list of dicts by 'name', case-insensitive
        self.all_artists_list = sorted(self.all_artists_list, key=lambda a: a['name'].lower())

    def reset_content_on_selection_change(self):
        for widget in self.content_area_frame.winfo_children():
            widget.destroy()
        self.current_content_placeholder_label = ttk.Label(
            self.content_area_frame,
            text="Selections changed. Click 'Proceed / Next Step'.",
            style="DataEntry.TLabel"
        )
        self.current_content_placeholder_label.pack(padx=10, pady=20, anchor="center")
        self.url_entry_var.set("")
        self.proceed_button.config(state=tk.NORMAL)  # <-- Always enable here

    def _all_mv_url_fields_filled(self):
        # Checks if all required fields for MV URL entry have data
        url = self.url_entry_var.get().strip()
        artist = self.primary_artist_var.get().strip()
        title = self.title_var.get().strip()
        date = self.date_var.get().strip()
        return bool(url and artist and title and date)

    def _show_mv_url_confirmation_popup(self):
        popup = tk.Toplevel(self)
        popup.title("Confirm Music Video Data")
        popup.geometry("900x450")
        popup.transient(self)
        popup.grab_set()
        frame = ttk.Frame(popup, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="Please review the entered data:", font=FONT_HEADER).pack(pady=(0,10))
        ttk.Label(frame, text=f"URL: {self.url_entry_var.get()}").pack(anchor="w")
        ttk.Label(frame, text=f"Primary Artist: {self.primary_artist_var.get()}").pack(anchor="w")
        ttk.Label(frame, text=f"Title: {self.title_var.get()}").pack(anchor="w")
        # Convert date for display
        raw_date = self.date_var.get().strip()
        formatted_date = self._convert_yymmdd_to_yyyy_mm_dd(raw_date)
        ttk.Label(frame, text=f"Date: {formatted_date if formatted_date else raw_date}").pack(anchor="w")
        # Song warning if no songs selected
        if not self.selected_song_titles:
            ttk.Label(frame, text="Warning: No song selected!", foreground="orange", font=(FONT_MAIN[0], FONT_MAIN[1], "bold")).pack(anchor="w", pady=(5,0))
        # Date warning if date is still default (today)
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        if formatted_date == today_str:
            ttk.Label(frame, text="Warning: Date is still set to today's date", foreground="orange", font=(FONT_MAIN[0], FONT_MAIN[1], "bold")).pack(anchor="w", pady=(2,0))
        # Music Video? checkbox
        mv_check_frame = ttk.Frame(frame)
        mv_check_frame.pack(anchor="w", pady=(15,0))
        ttk.Label(mv_check_frame, text="Music Video?").pack(side=tk.LEFT)
        is_mv_var = tk.BooleanVar(value=False)
        # Validation label
        validation_label = ttk.Label(frame, text="", foreground="red")
        validation_label.pack(anchor="w", pady=(5,0))
        def validate_confirm_state(*_):
            # 1. Music Video? must be checked
            if not is_mv_var.get():
                confirm_btn.config(state="disabled")
                validation_label.config(text="Please confirm this is a Music Video.")
                return
            # 2. URL must not already exist in file_path1
            url = self.url_entry_var.get().strip()
            conn = self.db_ops.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM music_videos WHERE file_path1 = ?", (url,))
            if cursor.fetchone():
                confirm_btn.config(state="disabled")
                validation_label.config(text="A music video with this URL already exists in file_path1.")
                return
            # 3. No entry with same artist and title
            title = self.title_var.get().strip()
            artist_name = self.primary_artist_var.get().strip()
            cursor.execute("SELECT artist_id FROM artists WHERE artist_name = ?", (artist_name,))
            row = cursor.fetchone()
            if not row:
                confirm_btn.config(state="disabled")
                validation_label.config(text="Artist not found in database.")
                return
            artist_id = row[0]
            cursor.execute("SELECT mv_id FROM music_videos WHERE title = ?", (title,))
            mv_ids = [r[0] for r in cursor.fetchall()]
            if mv_ids:
                for mv_id in mv_ids:
                    cursor.execute("SELECT 1 FROM music_video_artist_link WHERE mv_id = ? AND artist_id = ?", (mv_id, artist_id))
                    if cursor.fetchone():
                        confirm_btn.config(state="disabled")
                        validation_label.config(text="A music video with this artist and title already exists.")
                        return
            confirm_btn.config(state="normal")
            validation_label.config(text="")
        mv_checkbox = ttk.Checkbutton(mv_check_frame, variable=is_mv_var, command=validate_confirm_state)
        mv_checkbox.pack(side=tk.LEFT, padx=8)
        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=20)
        confirm_btn = ttk.Button(btn_frame, text="Confirm", state="disabled")
        confirm_btn.pack(side=tk.LEFT, padx=5)
        cancel_btn = ttk.Button(btn_frame, text="Cancel", command=popup.destroy)
        cancel_btn.pack(side=tk.LEFT, padx=5)
        validate_confirm_state()

    def handle_proceed(self):
        entry_type = self.entry_type_var.get()
        source_type = self.source_type_var.get()
        for widget in self.content_area_frame.winfo_children():
            widget.destroy()
        print(f"Proceeding with: Entry={entry_type}, Source={source_type}")
        if entry_type == "music_video" and source_type == "url":
            self.build_url_entry_ui(item_name="Music Video")
            # Only show confirmation popup if all required fields are filled
            if self._all_mv_url_fields_filled():
                self._show_mv_url_confirmation_popup()
            else:
                # Optionally, show a warning if user tries to proceed without all fields
                messagebox.showwarning("Missing Data", "Please fill in all required fields before proceeding.", parent=self)
            return
        if entry_type in ("performance", "music_video") and source_type == "url":
            self.build_url_entry_ui(item_name="Performance" if entry_type == "performance" else "Music Video")
            if self.all_fields_filled():
                self.confirm_and_save_entry(entry_type)
        else:
            ttk.Label(self.content_area_frame,
                      text=f"Placeholder UI for:\nEntry Type: {entry_type.replace('_', ' ').title()}\nSource Type: {source_type.replace('_', ' ').title()}",
                      style="DataEntry.TLabel", justify=tk.LEFT).pack(padx=10, pady=20, anchor="w")

    def handle_artist_combo_keypress(self, event):
        # print(f"DEBUG: Artist combo KeyPress: {event.keysym}, char: '{event.char}'")
        
        if event.char and event.char.isalnum(): 
            typed_char = event.char.lower()
            
            current_selection_text = self.primary_artist_var.get()
            # Ensure self.primary_artist_combo exists before trying to access its values
            if not hasattr(self, 'primary_artist_combo') or not self.primary_artist_combo.winfo_exists():
                return
            values = self.primary_artist_combo.cget("values")
            
            if not values or values[0] == "No artists in DB": # No actual artists to search
                return

            start_index = 0
            if current_selection_text in values:
                try:
                    current_idx = values.index(current_selection_text)
                    start_index = (current_idx + 1) % len(values) 
                except ValueError:
                    pass 
            
            search_order_indices = list(range(start_index, len(values))) + list(range(0, start_index))

            for i in search_order_indices:
                if values[i].lower().startswith(typed_char):
                    self.primary_artist_var.set(values[i])
                    self.primary_artist_combo.icursor(tk.END) 
                    # print(f"DEBUG: Jumped to {values[i]}")
                    return 

    def build_url_entry_ui(self, item_name):
        # Clear previous content to avoid stacking
        for widget in self.content_area_frame.winfo_children():
            widget.destroy()
        step_frame = ttk.Frame(self.content_area_frame, style="DataEntry.TFrame")
        step_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        url_frame = ttk.LabelFrame(step_frame, text=f"A. Enter {item_name} URL", style="DataEntry.TFrame", padding=10)
        url_frame.pack(fill="x", pady=5, anchor="n")

        ttk.Label(url_frame, text="URL:", style="DataEntry.TLabel").pack(anchor="w", pady=(0,2))
        url_entry = ttk.Entry(url_frame, textvariable=self.url_entry_var, width=70, style="DataEntry.TEntry")
        url_entry.pack(fill="x", pady=(0,5))
        self.after(100, lambda: url_entry.focus_set()) 

        # Remove the Check URL button, keep only the GO button
        go_button = ttk.Button(url_frame, text="GO", command=self.open_url_in_browser, style="DataEntry.TButton")
        go_button.pack(anchor="e", pady=2)

        artist_frame = ttk.Frame(step_frame, style="DataEntry.TFrame")
        artist_frame.pack(fill="x", pady=6)

        ttk.Label(artist_frame, text="Primary Artist:", style="DataEntry.TLabel").grid(row=0, column=0, sticky="w", pady=2, padx=2)

        artist_entry = ttk.Entry(
            artist_frame, textvariable=self.primary_artist_var, width=30, style="DataEntry.TEntry", state="readonly"
        )
        artist_entry.grid(row=0, column=1, sticky="ew", pady=2, padx=(2,0))

        select_btn = ttk.Button(
            artist_frame, text="Select...", command=self.show_artist_listbox_popup, style="DataEntry.TButton"
        )
        select_btn.grid(row=0, column=2, sticky="w", padx=(4,2))

        refresh_btn = ttk.Button(
            artist_frame, text="Refresh Artists", command=self.refresh_artist_list, style="DataEntry.TButton"
        )
        refresh_btn.grid(row=0, column=3, sticky="w", padx=(4,2))

        artist_frame.columnconfigure(1, weight=1)

        artist_buttons_frame = ttk.Frame(artist_frame, style="DataEntry.TFrame")
        artist_buttons_frame.grid(row=1, column=0, columnspan=4, pady=(10,5), sticky="ew")

        update_spotify_btn = ttk.Button(
            artist_buttons_frame, text="Update Artists (Spotify)",
            command=self.update_artists_from_spotify, style="DataEntry.TButton"
        )
        update_spotify_btn.pack(side=tk.LEFT, padx=2)

        add_secondary_btn = ttk.Button(
            artist_buttons_frame, text="Add Secondary Artist",
            command=self.add_secondary_artist_placeholder, style="DataEntry.TButton"
        )
        add_secondary_btn.pack(side=tk.LEFT, padx=2)
        
        # Secondary artist section (show if set)
        if self.secondary_artist_var.get():
            # show secondary artist widgets
            ttk.Label(artist_frame, text="Secondary Artist:", style="DataEntry.TLabel").grid(row=2, column=0, sticky="w", pady=2, padx=2)
            secondary_entry = ttk.Entry(
                artist_frame, textvariable=self.secondary_artist_var, width=30, style="DataEntry.TEntry", state="readonly"
            )
            secondary_entry.grid(row=2, column=1, sticky="ew", pady=2, padx=(2,0))
            select_secondary_btn = ttk.Button(
                artist_frame, text="Select...", command=self.show_secondary_artist_listbox_popup, style="DataEntry.TButton"
            )
            select_secondary_btn.grid(row=2, column=2, sticky="w", padx=(4,2))
            remove_secondary_btn = ttk.Button(
                artist_frame, text="Remove", command=self.remove_secondary_artist, style="DataEntry.TButton"
            )
            remove_secondary_btn.grid(row=2, column=3, sticky="w", padx=(4,2))

        # SONG SELECTION SECTION
        song_frame = ttk.Frame(step_frame, style="DataEntry.TFrame")
        song_frame.pack(fill="x", pady=(10,0))

        ttk.Label(song_frame, text="Song(s):", style="DataEntry.TLabel").grid(row=0, column=0, sticky="w", pady=2, padx=2)

        # Show selected songs
        if self.selected_song_titles:
            for idx, title in enumerate(self.selected_song_titles):
                ttk.Label(song_frame, text=title, style="DataEntry.TLabel").grid(row=idx+1, column=1, sticky="w", padx=(10,2))
                remove_btn = ttk.Button(song_frame, text="Remove", style="DataEntry.TButton",
                                        command=lambda i=idx: self.remove_selected_song(i))
                remove_btn.grid(row=idx+1, column=2, padx=(4,2), sticky="w")
        else:
            ttk.Label(song_frame, text="No songs selected.", style="DataEntry.TLabel").grid(row=1, column=1, sticky="w", padx=(10,2))

        add_song_btn = ttk.Button(song_frame, text="Add Song(s)", style="DataEntry.TButton", command=self.show_song_selection_popup)
        add_song_btn.grid(row=0, column=2, padx=(4,2), sticky="w")

        title_frame = ttk.Frame(step_frame, style="DataEntry.TFrame")
        title_frame.pack(fill="x", pady=(10,0))

        ttk.Label(title_frame, text="Title:", style="DataEntry.TLabel").grid(row=0, column=0, sticky="w", pady=2, padx=2)
        title_entry = ttk.Entry(title_frame, textvariable=self.title_var, width=70, style="DataEntry.TEntry")
        title_entry.grid(row=0, column=1, sticky="ew", pady=2, padx=(2,0))
        title_frame.columnconfigure(1, weight=1)

        # DATE ENTRY SECTION
        date_frame = ttk.Frame(step_frame, style="DataEntry.TFrame")
        date_frame.pack(fill="x", pady=(10,0))

        ttk.Label(date_frame, text="Date (YYMMDD):", style="DataEntry.TLabel").grid(row=0, column=0, sticky="w", pady=2, padx=2)
        # Only clear the date if the user is starting a new entry, not on every UI rebuild
        if not self.date_var.get():
            self.date_var.set("")
        self.date_entry = ttk.Entry(date_frame, textvariable=self.date_var, width=12, style="DataEntry.TEntry")
        self.date_entry.grid(row=0, column=1, sticky="w", pady=2, padx=(2,0))
        ttk.Label(date_frame, text="(e.g. 240530)", style="DataEntry.TLabel").grid(row=0, column=2, sticky="w", padx=(8,2))

    def update_artists_from_spotify(self):
        # Paths to your scripts
        base_dir = os.path.dirname(__file__)
        album_importer = os.path.join(base_dir, "accesories/spotify_data/spotify_album_importer.py")
        artist_info_importer = os.path.join(base_dir, "accesories/spotify_data/spotify_artist_info_importer.py")
        try:
            subprocess.run([sys.executable, album_importer], check=True)
            subprocess.run([sys.executable, artist_info_importer], check=True)
            self.load_initial_data()
            messagebox.showinfo("Artists Updated", "Artists have been updated and enriched from Spotify.", parent=self)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update artists from Spotify:\n{e}", parent=self)

    def add_secondary_artist_placeholder(self):
        # Set a placeholder so the secondary artist field appears
        self.secondary_artist_var.set("Select...")
        self.build_url_entry_ui(item_name="Performance" if self.entry_type_var.get() == "performance" else "Music Video")

    def check_entered_url(self):
        url = self.url_entry_var.get()
        if not url:
            messagebox.showwarning("Input Required", "Please enter a URL.", parent=self)
            return
        if url.startswith("http://") or url.startswith("https://"):
            messagebox.showinfo("URL Check", f"URL seems valid:\n{url}", parent=self)
        else:
            messagebox.showerror("URL Check", f"URL does not seem valid:\n{url}", parent=self)
        # print(f"Checking URL: {url") # Keep for console feedback if desired

    def close_window(self):
        if hasattr(self.master_app, 'data_entry_window_instance') and \
           self.master_app.data_entry_window_instance == self:
            self.master_app.data_entry_window_instance = None
        self.destroy()

    def show_artist_listbox_popup(self):
        if not self.all_artists_list:
            messagebox.showinfo("No Artists", "No artists available in the database.", parent=self)
            return

        popup = tk.Toplevel(self)
        popup.title("Select Primary Artist")
        popup.configure(bg=DARK_BG)
        popup.geometry("350x400+%d+%d" % (self.winfo_rootx()+100, self.winfo_rooty()+100))
        popup.transient(self)
        popup.grab_set()

        # Frame for listbox and scrollbar
        frame = tk.Frame(popup, bg=DARK_BG)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        scrollbar = tk.Scrollbar(frame, orient="vertical")
        listbox = tk.Listbox(
            frame, font=FONT_MAIN, bg="#333a40", fg=BRIGHT_FG, selectbackground=ACCENT,
            selectforeground="#f1fa8c", activestyle="none", highlightthickness=0,
            yscrollcommand=scrollbar.set
        )
        scrollbar.config(command=listbox.yview)
        scrollbar.pack(side="right", fill="y")
        listbox.pack(side="left", fill="both", expand=True)

        artist_names = [artist['name'] for artist in self.all_artists_list]
        for name in artist_names:
            listbox.insert(tk.END, name)

        def on_select(event=None):
            selection = listbox.curselection()
            if selection:
                artist_name = listbox.get(selection[0])
                self.primary_artist_var.set(artist_name)
                popup.destroy()

        def on_key(event):
            # Jump to letter
            if event.char and event.char.isprintable():
                typed = event.char.lower()
                for idx, name in enumerate(artist_names):
                    if name.lower().startswith(typed):
                        listbox.selection_clear(0, tk.END)
                        listbox.selection_set(idx)
                        listbox.see(idx)
                        break
            elif event.keysym in ("Return", "KP_Enter"):
                on_select()
            elif event.keysym == "Escape":
                popup.destroy()

        listbox.bind("<Double-Button-1>", on_select)
        listbox.bind("<Return>", on_select)
        listbox.bind("<Key>", on_key)
        listbox.focus_set()

        # Pre-select current value if set
        current = self.primary_artist_var.get()
        if current in artist_names:
            idx = artist_names.index(current)
            listbox.selection_set(idx)
            listbox.see(idx)

    def refresh_artist_list(self):
        self.load_initial_data()
        messagebox.showinfo("Artists Refreshed", "Artist list has been refreshed from the database.", parent=self)

    def show_secondary_artist_listbox_popup(self):
        if not self.all_artists_list:
            messagebox.showinfo("No Artists", "No artists available in the database.", parent=self)
            return

        popup = tk.Toplevel(self)
        popup.title("Select Secondary Artist")
        popup.configure(bg=DARK_BG)
        popup.geometry("350x400+%d+%d" % (self.winfo_rootx()+120, self.winfo_rooty()+120))
        popup.transient(self)
        popup.grab_set()

        frame = tk.Frame(popup, bg=DARK_BG)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        scrollbar = tk.Scrollbar(frame, orient="vertical")
        listbox = tk.Listbox(
            frame, font=FONT_MAIN, bg="#333a40", fg=BRIGHT_FG, selectbackground=ACCENT,
            selectforeground="#f1fa8c", activestyle="none", highlightthickness=0,
            yscrollcommand=scrollbar.set
        )
        scrollbar.config(command=listbox.yview)
        scrollbar.pack(side="right", fill="y")
        listbox.pack(side="left", fill="both", expand=True)

        artist_names = [artist['name'] for artist in self.all_artists_list]
        for name in artist_names:
            listbox.insert(tk.END, name)

        def on_select(event=None):
            selection = listbox.curselection()
            if selection:
                artist_name = listbox.get(selection[0])
                self.secondary_artist_var.set(artist_name)  # <-- FIXED: set secondary, not primary
                popup.destroy()
                self.build_url_entry_ui(item_name="Performance" if self.entry_type_var.get() == "performance" else "Music Video")

        def on_key(event):
            if event.char and event.char.isprintable():
                typed = event.char.lower()
                for idx, name in enumerate(artist_names):
                    if name.lower().startswith(typed):
                        listbox.selection_clear(0, tk.END)
                        listbox.selection_set(idx)
                        listbox.see(idx)
                        break
            elif event.keysym in ("Return", "KP_Enter"):
                on_select()
            elif event.keysym == "Escape":
                popup.destroy()

        listbox.bind("<Double-Button-1>", on_select)
        listbox.bind("<Return>", on_select)
        listbox.bind("<Key>", on_key)
        listbox.focus_set()

        # Pre-select current value if set
        current = self.secondary_artist_var.get()
        if current in artist_names:
            idx = artist_names.index(current)
            listbox.selection_set(idx)
            listbox.see(idx)

    def remove_secondary_artist(self):
        self.secondary_artist_var.set("")
        self.build_url_entry_ui(item_name="Performance" if self.entry_type_var.get() == "performance" else "Music Video")

    def get_songs_for_selected_artists(self):
        # Get artist IDs
        artist_names = [self.primary_artist_var.get()]
        if self.secondary_artist_var.get().strip():
            artist_names.append(self.secondary_artist_var.get())
        artist_ids = []
        for name in artist_names:
            for artist in self.all_artists_list:
                if artist['name'] == name:
                    artist_ids.append(artist['id'])
        if not artist_ids:
            return []

        # Query songs for these artist_ids
        placeholders = ",".join("?" for _ in artist_ids)
        query = f"""
            SELECT DISTINCT s.song_id, s.song_title
            FROM songs s
            JOIN song_artist_link sal ON s.song_id = sal.song_id
            WHERE sal.artist_id IN ({placeholders})
            ORDER BY s.song_title COLLATE NOCASE
        """
        conn = self.db_ops.get_db_connection()
        if not conn:
            return []
        try:
            cursor = conn.cursor()
            cursor.execute(query, artist_ids)
            return cursor.fetchall()  # List of (song_id, song_title)
        except Exception as e:
            print(f"Error fetching songs for artists: {e}")
            return []

    def show_song_selection_popup(self):
        songs = self.get_songs_for_selected_artists()
        if not songs:
            messagebox.showinfo("No Songs", "No songs found for the selected artist(s).", parent=self)
            return

        # Build a mapping from title to all song_ids with that title
        title_to_song_ids = {}
        for song_id, title in songs:
            title_to_song_ids.setdefault(title, []).append(song_id)
        unique_titles = sorted(title_to_song_ids.keys(), key=lambda t: t.lower())

        popup = tk.Toplevel(self)
        popup.title("Select Song(s)")
        popup.configure(bg=DARK_BG)
        popup.geometry("400x500+%d+%d" % (self.winfo_rootx()+140, self.winfo_rooty()+140))
        popup.transient(self)
        popup.grab_set()

        frame = tk.Frame(popup, bg=DARK_BG)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        scrollbar = tk.Scrollbar(frame, orient="vertical")
        listbox = tk.Listbox(
            frame, font=FONT_MAIN, bg="#333a40", fg=BRIGHT_FG, selectbackground=ACCENT,
            selectforeground="#f1fa8c", activestyle="none", highlightthickness=0,
            yscrollcommand=scrollbar.set, selectmode=tk.MULTIPLE
        )
        scrollbar.config(command=listbox.yview)
        scrollbar.pack(side="right", fill="y")
        listbox.pack(side="left", fill="both", expand=True)

        for title in unique_titles:
            listbox.insert(tk.END, title)

        # Pre-select already selected songs (if any of their song_ids are in self.selected_song_ids)
        for idx, title in enumerate(unique_titles):
            song_ids = title_to_song_ids[title]
            if any(song_id in self.selected_song_ids for song_id in song_ids):
                listbox.selection_set(idx)

        def on_ok():
            selected_indices = listbox.curselection()
            selected_titles = [unique_titles[i] for i in selected_indices]
            # For each selected title, collect all song_ids for that title
            selected_song_ids = []
            for title in selected_titles:
                selected_song_ids.extend(title_to_song_ids[title])
            self.selected_song_ids = selected_song_ids
            self.selected_song_titles = selected_titles
            popup.destroy()
            self.build_url_entry_ui(item_name="Performance" if self.entry_type_var.get() == "performance" else "Music Video")
            self.update_title_from_songs()  # Update title after song selection

        def on_cancel():
            popup.destroy()

        btn_frame = tk.Frame(popup, bg=DARK_BG)
        btn_frame.pack(fill="x", pady=(10,0))
        ok_btn = ttk.Button(btn_frame, text="OK", command=on_ok, style="DataEntry.TButton")
        ok_btn.pack(side=tk.RIGHT, padx=4)
        cancel_btn = ttk.Button(btn_frame, text="Cancel", command=on_cancel, style="DataEntry.TButton")
        cancel_btn.pack(side=tk.RIGHT, padx=4)

        listbox.focus_set()

    def remove_selected_song(self, idx):
        if 0 <= idx < len(self.selected_song_ids):
            del self.selected_song_ids[idx]
            del self.selected_song_titles[idx]
            self.build_url_entry_ui(item_name="Performance" if self.entry_type_var.get() == "performance" else "Music Video")

    def on_url_change(self, *args):
        url = self.url_entry_var.get()
        if url.startswith("http://") or url.startswith("https://"):
            self.proceed_button.config(state=tk.NORMAL)
        else:
            self.proceed_button.config(state=tk.DISABLED)

    def open_url_in_browser(self):
        url = self.url_entry_var.get()
        if url.startswith("http://") or url.startswith("https://"):
            webbrowser.open(url)
        else:
            messagebox.showerror("Invalid URL", "Please enter a valid URL (starting with http:// or https://).", parent=self)

    def update_title_from_songs(self):
        # Only auto-update if the user hasn't changed it manually (optional: add a flag if you want)
        self.title_var.set(", ".join(self.selected_song_titles))

    def confirm_and_save_entry(self, entry_type):
        # Gather all data
        url = self.url_entry_var.get()
        primary_artist = self.primary_artist_var.get()
        secondary_artist = self.secondary_artist_var.get().strip() or None
        songs = self.selected_song_titles
        title = self.title_var.get()
        raw_date = self.date_var.get().strip()
        date = self._convert_yymmdd_to_yyyy_mm_dd(raw_date)
        score = 0 if entry_type == "music_video" else None

        summary = f"Type: {entry_type.replace('_', ' ').title()}\n"
        summary += f"URL: {url}\n"
        summary += f"Primary Artist: {primary_artist}\n"
        if secondary_artist:
            summary += f"Secondary Artist: {secondary_artist}\n"
        summary += f"Songs: {', '.join(songs)}\n"
        summary += f"Title: {title}\n"
        summary += f"Date: {date}\n"
        if entry_type == "music_video":
            summary += f"Score: 0 (fixed)\n"
        else:
            summary += f"Score: (to be set later)\n"

        if messagebox.askokcancel("Confirm Entry", f"Please confirm the following data:\n\n{summary}", parent=self):
            try:
                if entry_type == "music_video":
                    self.db_ops.insert_music_video(
                        title=title,
                        release_date=date,
                        file_url=url,
                        score=0,
                        artist_names=[primary_artist] + ([secondary_artist] if secondary_artist else []),
                        song_ids=self.selected_song_ids
                    )
                else:
                    # For performance, call a similar db_ops.insert_performance(...)
                    pass
                messagebox.showinfo("Success", "Entry saved to database.", parent=self)
                self.close_window()
            except Exception as e:
                messagebox.showerror("Database Error", f"Failed to save entry: {e}", parent=self)

    def _convert_yymmdd_to_yyyy_mm_dd(self, yymmdd):
        # Converts yymmdd string to yyyy-mm-dd, returns None if invalid
        if len(yymmdd) != 6 or not yymmdd.isdigit():
            return None
        year = int(yymmdd[:2])
        month = yymmdd[2:4]
        day = yymmdd[4:6]
        year += 2000 if year < 50 else 1900  # 00-49: 2000s, 50-99: 1900s
        try:
            return f"{year:04d}-{month}-{day}"
        except Exception:
            return None
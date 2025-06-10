# data_entry_ui.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog # Added filedialog
import subprocess
import sys
import os # Added os for os.path.basename
import webbrowser
import datetime
import config  # For MPV_PLAYER_PATH
try:
    from tkcalendar import DateEntry
    HAS_TKCALENDAR = True
except ImportError:
    HAS_TKCALENDAR = False

# Modularized imports (will be needed later if not already passed, e.g. config)
# import config
import utils  # For extract_date_from_filepath
# db_operations will be passed in constructor

# Constants
DARK_BG = "#222222"
BRIGHT_FG = "#f8f8f2"
ACCENT = "#44475a"
FONT_MAIN = ("Courier New", 15)
FONT_HEADER = ("Courier New", 15, "bold")
FONT_BUTTON = ("Arial", 15, "bold")
FONT_ENTRY_DATA_UI = ("Courier New", 15)


class DataEntryWindow(tk.Toplevel):
    def __init__(self, master, db_ops): 
        super().__init__(master)
        self.title("Add Database Entry")
        self.geometry("900x1100")
        self.configure(bg=DARK_BG)
        self.transient(master)
        self.grab_set()

        self.master_app = master
        self.db_ops = db_ops

        # Create radiobutton images
        self.radio_unchecked_img, self.radio_checked_img = self._create_radiobutton_images(size=24, indicator_size_ratio=0.5)
        self.entry_type_radios = [] # To store entry type radio buttons
        self.source_type_radios = [] # To store source type radio buttons

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("DataEntry.TFrame", background=DARK_BG)
        style.configure("DataEntry.TLabel", background=DARK_BG, foreground=BRIGHT_FG, font=FONT_MAIN)
        style.configure("DataEntry.TLabelframe.Label", background=DARK_BG, foreground=BRIGHT_FG, font=("Courier New", 15, "bold"))
        style.configure("DataEntry.TLabelframe", background=DARK_BG)
        style.configure("DataEntry.TRadiobutton", background=DARK_BG, foreground=BRIGHT_FG, font=FONT_MAIN,
                        relief=tk.FLAT, padding=(10, 5))
        style.map("DataEntry.TRadiobutton",
                  background=[('active', DARK_BG)])
        # Override layout to remove the default small indicator circle
        style.layout("DataEntry.TRadiobutton", [
            ('Radiobutton.padding', {'sticky':'nswe','children':[
                ('Radiobutton.focus', {'sticky':'nswe','children':[
                    ('Radiobutton.label', {'sticky':'nswe'})
                ]})
            ]})
        ])
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
            arrowcolor=BRIGHT_FG,
            background=DARK_BG  # Ensure dropdown and arrow use dark background
        )
        style.map("DataEntry.TCombobox",
            fieldbackground=[('readonly', DARK_BG), ('!readonly', DARK_BG)],
            foreground=[('readonly', BRIGHT_FG), ('!readonly', BRIGHT_FG)],
            arrowcolor=[('readonly', BRIGHT_FG), ('!readonly', BRIGHT_FG)],
            background=[('readonly', DARK_BG), ('!readonly', DARK_BG)]
        )

        main_frame = ttk.Frame(self, padding="20", style="DataEntry.TFrame")
        main_frame.pack(fill=tk.BOTH, expand=True)

        self.entry_type_var = tk.StringVar(value="performance")  # default performance
        self.source_type_var = tk.StringVar(value="local_file")  # default local file
        self.title_var = tk.StringVar()

        # Remove default date assignment so the date field starts empty
        self.date_var = tk.StringVar()

        selection_outer_frame = ttk.Frame(main_frame, style="DataEntry.TFrame")
        selection_outer_frame.pack(pady=0, fill="x")

        type_frame = ttk.LabelFrame(selection_outer_frame, text="Entry Type", style="DataEntry.TLabelframe", padding=(10, 8))
        type_frame.pack(pady=5, fill="x")

        rb_perf = ttk.Radiobutton(type_frame, text="Performance", variable=self.entry_type_var,
                        value="performance", style="DataEntry.TRadiobutton", 
                        image=self.radio_unchecked_img, compound='left')
        rb_perf.config(command=lambda: (self.reset_content_on_selection_change(), self._update_radio_button_images(self.entry_type_var, self.entry_type_radios)))
        rb_perf.pack(side=tk.LEFT, padx=20, pady=10)
        self.entry_type_radios.append(rb_perf)

        rb_mv = ttk.Radiobutton(type_frame, text="Music Video", variable=self.entry_type_var,
                        value="music_video", style="DataEntry.TRadiobutton",
                        image=self.radio_unchecked_img, compound='left')
        rb_mv.config(command=lambda: (self.reset_content_on_selection_change(), self._update_radio_button_images(self.entry_type_var, self.entry_type_radios)))
        rb_mv.pack(side=tk.LEFT, padx=20, pady=10)
        self.entry_type_radios.append(rb_mv)
        
        self._update_radio_button_images(self.entry_type_var, self.entry_type_radios) # Initial image update

        source_frame = ttk.LabelFrame(selection_outer_frame, text="Source Type", style="DataEntry.TLabelframe", padding=(10, 8))
        source_frame.pack(pady=5, fill="x")

        rb_url = ttk.Radiobutton(source_frame, text="URL", variable=self.source_type_var,
                        value="url", style="DataEntry.TRadiobutton",
                        image=self.radio_unchecked_img, compound='left')
        rb_url.config(command=lambda: (self.reset_content_on_selection_change(), self._update_radio_button_images(self.source_type_var, self.source_type_radios)))
        rb_url.pack(side=tk.LEFT, padx=20, pady=10)
        self.source_type_radios.append(rb_url)

        rb_local = ttk.Radiobutton(source_frame, text="Local File", variable=self.source_type_var,
                        value="local_file", style="DataEntry.TRadiobutton",
                        image=self.radio_unchecked_img, compound='left')
        rb_local.config(command=lambda: (self.reset_content_on_selection_change(), self._update_radio_button_images(self.source_type_var, self.source_type_radios)))
        rb_local.pack(side=tk.LEFT, padx=20, pady=10)
        self.source_type_radios.append(rb_local)

        self._update_radio_button_images(self.source_type_var, self.source_type_radios) # Initial image update
        
        # details area without framing label
        self.content_area_frame = ttk.Frame(main_frame, style="DataEntry.TFrame")
        self.content_area_frame.pack(pady=10, fill=tk.BOTH, expand=True)
        
        self.current_content_placeholder_label = ttk.Label(self.content_area_frame, text="Select options above and click 'Proceed / Next Step'.", style="DataEntry.TLabel")
        self.current_content_placeholder_label.pack(padx=10, pady=20, anchor="center")

        self.url_entry_var = tk.StringVar()
        self.primary_artist_var = tk.StringVar()
        self.secondary_artist_var = tk.StringVar()
        self.all_artists_list = [] 
        self.selected_song_ids = []  # List of selected song_id
        self.selected_song_titles = []  # Parallel list of song titles for display

        # Variables for local file processing
        self.selected_local_files = [] 
        self.local_files_display_var = tk.StringVar()
        self.local_files_display_var.set("No files selected.") # Initial value
        self.local_file_validation_label_var = tk.StringVar() # For validation messages

        button_frame = ttk.Frame(main_frame, style="DataEntry.TFrame")
        button_frame.pack(fill="x", pady=(10, 0), side=tk.BOTTOM)

        self.proceed_button = ttk.Button(button_frame, text="Proceed / Next Step", command=self.handle_proceed, style="DataEntry.TButton")
        self.proceed_button.pack(side=tk.RIGHT, padx=5)

        self.cancel_button = ttk.Button(button_frame, text="Cancel", command=self.close_window, style="DataEntry.TButton")
        self.cancel_button.pack(side=tk.RIGHT, padx=5)

        # Save Entry button, initially hidden
        self.save_entry_button = ttk.Button(button_frame, text="Save Entry", command=self._attempt_save_local_entry, style="DataEntry.TButton")
        # Do not pack yet; will be packed after Proceed

        self.protocol("WM_DELETE_WINDOW", self.close_window)
        self.load_initial_data() 
        self.focus_set()

        self.url_entry_var.trace_add("write", self.on_url_change)

        # New variables for show type and resolution choices
        self.show_type_choices = []
        self.resolution_choices = []
        self._load_showtype_and_resolution_choices()

    def _update_radio_button_images(self, group_variable, radio_buttons):
        """Updates the images for a group of radio buttons based on the variable's state."""
        current_value = group_variable.get()
        for rb in radio_buttons:
            rb_value = rb.cget("value") 
            if rb_value == current_value:
                rb.config(image=self.radio_checked_img)
            else:
                rb.config(image=self.radio_unchecked_img)

    def _create_radiobutton_images(self, size=24, indicator_size_ratio=0.5, border_width=2):
        """Creates custom images for radio button indicators."""
        from tkinter import PhotoImage
        
        fg_color = BRIGHT_FG
        bg_color = DARK_BG
        accent_color = ACCENT
        
        # Unchecked image (empty circle)
        unchecked_img = PhotoImage(width=size, height=size)
        unchecked_img.put(bg_color, to=(0, 0, size, size)) # Fill background

        center_x, center_y = size // 2, size // 2
        radius = (size // 2) - border_width

        for x in range(size):
            for y in range(size):
                dist_sq = (x - center_x)**2 + (y - center_y)**2
                # Draw outer border (slightly thicker)
                if radius**2 <= dist_sq < (radius + border_width)**2 :
                    unchecked_img.put(fg_color, (x, y))
                # Fill inside with background for truly empty circle
                elif dist_sq < radius**2:
                     unchecked_img.put(bg_color, (x,y))


        # Checked image (circle with smaller filled circle)
        checked_img = PhotoImage(width=size, height=size)
        checked_img.put(bg_color, to=(0, 0, size, size)) # Fill background
        
        indicator_radius = int(radius * indicator_size_ratio)

        for x in range(size):
            for y in range(size):
                dist_sq = (x - center_x)**2 + (y - center_y)**2
                # Draw outer border
                if radius**2 <= dist_sq < (radius + border_width)**2:
                    checked_img.put(fg_color, (x, y))
                # Draw inner filled circle (indicator)
                elif dist_sq < indicator_radius**2:
                    checked_img.put(fg_color, (x, y))
                # Fill space between inner circle and outer border with background
                elif indicator_radius**2 <= dist_sq < radius**2:
                    checked_img.put(bg_color, (x,y))

        return unchecked_img, checked_img

    def load_initial_data(self):
        self.all_artists_list = self.db_ops.get_all_artists()
        # Sort the list of dicts by 'name', case-insensitive
        self.all_artists_list = sorted(self.all_artists_list, key=lambda a: a['name'].lower())

    def reset_form_fields(self):
        """Reset all form fields to prepare for a new entry"""
        # Clear all primary form variables
        self.url_entry_var.set("")
        self.primary_artist_var.set("")
        self.secondary_artist_var.set("")
        self.title_var.set("")
        self.date_var.set("")
        
        # Clear song selections
        self.selected_song_ids = []
        self.selected_song_titles = []
        
        # Clear local file selections
        self.selected_local_files = []
        self.local_files_display_var.set("No files selected.")
        self.local_file_validation_label_var.set("")
        
        # Clear show type and resolution for performances (if they exist)
        if hasattr(self, 'show_type_var'):
            self.show_type_var.set("")
        if hasattr(self, 'resolution_var'):
            self.resolution_var.set("")
        
        # Reset UI to initial state
        for widget in self.content_area_frame.winfo_children():
            widget.destroy()
        self.current_content_placeholder_label = ttk.Label(
            self.content_area_frame,
            text="Select options above and click 'Proceed / Next Step'.",
            style="DataEntry.TLabel"
        )
        self.current_content_placeholder_label.pack(padx=10, pady=20, anchor="center")
        
        # Reset buttons to initial state
        self.proceed_button.config(state=tk.NORMAL)
        self.proceed_button.pack(side=tk.RIGHT, padx=5)
        self.save_entry_button.pack_forget()
        self.cancel_button.pack(side=tk.RIGHT, padx=5)

    def _load_showtype_and_resolution_choices(self):
        # Query the DB for all unique show_type and resolution values
        try:
            conn = self.db_ops.get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT show_type FROM performances WHERE show_type IS NOT NULL AND TRIM(show_type) != '' ORDER BY show_type;")
            self.show_type_choices = [row[0] for row in cur.fetchall() if row[0]]
            
            # Load resolution choices from both performances and music_videos tables
            resolution_set = set()
            cur.execute("SELECT DISTINCT resolution FROM performances WHERE resolution IS NOT NULL AND TRIM(resolution) != '' ORDER BY resolution;")
            resolution_set.update(row[0] for row in cur.fetchall() if row[0])
            cur.execute("SELECT DISTINCT resolution FROM music_videos WHERE resolution IS NOT NULL AND TRIM(resolution) != '' ORDER BY resolution;")
            resolution_set.update(row[0] for row in cur.fetchall() if row[0])
            
            self.resolution_choices = sorted(list(resolution_set), key=lambda s: s.lower())
        except Exception as e:
            self.show_type_choices = []
            self.resolution_choices = []

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
        # Reset local file specific variables
        self.selected_local_files = []
        self.local_files_display_var.set("No files selected.")
        
        self.proceed_button.config(state=tk.NORMAL)  # <-- Always enable here

    def _all_mv_url_fields_filled(self):
        # Checks if all required fields for MV URL entry have data
        url = self.url_entry_var.get().strip()
        artist = self.primary_artist_var.get().strip()
        title = self.title_var.get().strip()
        date = self.date_var.get().strip()
        return bool(url and artist and title and date)

    def _all_performance_url_fields_filled(self):
        url = self.url_entry_var.get().strip()
        artist = self.primary_artist_var.get().strip()
        title = self.title_var.get().strip()
        date = self.date_var.get().strip()
        show_type = self.show_type_var.get().strip() if hasattr(self, 'show_type_var') else ''
        resolution = self.resolution_var.get().strip() if hasattr(self, 'resolution_var') else ''
        return bool(url and artist and title and date and show_type and resolution)

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
        if self.secondary_artist_var.get().strip():
            ttk.Label(frame, text=f"Secondary Artist: {self.secondary_artist_var.get().strip()}").pack(anchor="w")
        ttk.Label(frame, text=f"Title: {self.title_var.get()}").pack(anchor="w")
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
        mv_checkbox = ttk.Checkbutton(mv_check_frame, variable=is_mv_var)
        mv_checkbox.pack(side=tk.LEFT, padx=8)
        # Validation label
        validation_label = ttk.Label(frame, text="", foreground="red")
        validation_label.pack(anchor="w", pady=(5,0))
        def validate_confirm_state(*_):
            if not is_mv_var.get():
                confirm_btn.config(state="disabled")
                validation_label.config(text="Please confirm this is a Music Video.")
                return
            url = self.url_entry_var.get().strip()
            title = self.title_var.get().strip()
            artist_name = self.primary_artist_var.get().strip()
            date = self.date_var.get().strip()
            if not (url and title and artist_name and date):
                confirm_btn.config(state="disabled")
                validation_label.config(text="URL, artist, title, and date are required.")
                return
            conn = self.db_ops.get_db_connection()
            cursor = conn.cursor()
            # 1. URL must not already exist in file_url
            cursor.execute("SELECT 1 FROM music_videos WHERE file_url = ?", (url,)) # Changed file_path1 to file_url
            if cursor.fetchone():
                confirm_btn.config(state="disabled")
                validation_label.config(text="A music video with this URL already exists.") # Updated message
                return
            # 2. Primary artist must exist
            cursor.execute("SELECT artist_id FROM artists WHERE artist_name = ?", (artist_name,))
            row = cursor.fetchone()
            if not row:
                confirm_btn.config(state="disabled")
                validation_label.config(text="Primary artist not found in database.")
                return
            # 3. No previous record with same artist and title
            cursor.execute("""
                SELECT 1 FROM music_videos mv
                JOIN music_video_artist_link mval ON mv.mv_id = mval.mv_id
                JOIN artists a ON mval.artist_id = a.artist_id
                WHERE mv.title = ? AND a.artist_name = ?
            """, (title, artist_name))
            if cursor.fetchone():
                confirm_btn.config(state="disabled")
                validation_label.config(text="A music video with this artist and title already exists.")
                return
            confirm_btn.config(state="normal")
            validation_label.config(text="")
        mv_checkbox.config(command=validate_confirm_state)
        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=20)
        def on_confirm():
            try:
                # Pass source_type="url"
                self.confirm_and_save_entry("music_video", source_type="url")
                popup.destroy()
            except Exception as e:
                messagebox.showerror("Database Error", f"Failed to save entry: {e}", parent=self)
        confirm_btn = ttk.Button(btn_frame, text="Confirm", state="disabled", command=on_confirm)
        confirm_btn.pack(side=tk.LEFT, padx=5)
        cancel_btn = ttk.Button(btn_frame, text="Cancel", command=popup.destroy)
        cancel_btn.pack(side=tk.LEFT, padx=5)
        validate_confirm_state()

    def _show_performance_url_confirmation_popup(self):
        popup = tk.Toplevel(self)
        popup.title("Confirm Performance Data")
        popup.geometry("900x450")
        popup.transient(self)
        popup.grab_set()
        frame = ttk.Frame(popup, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="Please review the entered data:", font=FONT_HEADER).pack(pady=(0,10))
        ttk.Label(frame, text=f"URL: {self.url_entry_var.get()}").pack(anchor="w")
        ttk.Label(frame, text=f"Primary Artist: {self.primary_artist_var.get()}").pack(anchor="w")
        if self.secondary_artist_var.get().strip():
            ttk.Label(frame, text=f"Secondary Artist: {self.secondary_artist_var.get().strip()}").pack(anchor="w")
        ttk.Label(frame, text=f"Title: {self.title_var.get()}").pack(anchor="w")
        raw_date = self.date_var.get().strip()
        formatted_date = self._convert_yymmdd_to_yyyy_mm_dd(raw_date)
        ttk.Label(frame, text=f"Date: {formatted_date if formatted_date else raw_date}").pack(anchor="w")
        ttk.Label(frame, text=f"Show Type: {self.show_type_var.get().strip() if hasattr(self, 'show_type_var') else ''}").pack(anchor="w")
        ttk.Label(frame, text=f"Resolution: {self.resolution_var.get().strip() if hasattr(self, 'resolution_var') else ''}").pack(anchor="w")
        if not self.selected_song_titles:
            ttk.Label(frame, text="Warning: No song selected!", foreground="orange", font=(FONT_MAIN[0], FONT_MAIN[1], "bold")).pack(anchor="w", pady=(5,0))
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        if formatted_date == today_str:
            ttk.Label(frame, text="Warning: Date is still set to today's date", foreground="orange", font=(FONT_MAIN[0], FONT_MAIN[1], "bold")).pack(anchor="w", pady=(2,0))
        validation_label = ttk.Label(frame, text="", foreground="red")
        validation_label.pack(anchor="w", pady=(5,0))
        def validate_confirm_state(*_):
            url = self.url_entry_var.get().strip()
            title = self.title_var.get().strip()
            artist_name = self.primary_artist_var.get().strip()
            date = self._convert_yymmdd_to_yyyy_mm_dd(self.date_var.get().strip())
            show_type = self.show_type_var.get().strip() if hasattr(self, 'show_type_var') else ''
            resolution = self.resolution_var.get().strip() if hasattr(self, 'resolution_var') else ''
            if not (url and title and artist_name and date and show_type and resolution):
                confirm_btn.config(state="disabled")
                validation_label.config(text="All fields (URL, artist, title, date, show type, resolution) are required.")
                return
            conn = self.db_ops.get_db_connection()
            cursor = conn.cursor()
            # 1. URL must not exist in file_url
            cursor.execute("SELECT 1 FROM performances WHERE file_url = ?", (url,)) # Changed file_path1 to file_url
            if cursor.fetchone():
                confirm_btn.config(state="disabled")
                validation_label.config(text="A performance with this URL already exists.") # Updated message
                return
            # 2. Primary artist must exist
            cursor.execute("SELECT artist_id FROM artists WHERE artist_name = ?", (artist_name,))
            row = cursor.fetchone()
            if not row:
                confirm_btn.config(state="disabled")
                validation_label.config(text="Primary artist not found in database.")
                return
            # 3. No previous record with same artist, title, and date
            cursor.execute("""
                SELECT 1 FROM performances p
                JOIN performance_artist_link pal ON p.performance_id = pal.performance_id
                JOIN artists a ON pal.artist_id = a.artist_id
                WHERE p.title = ? AND p.performance_date = ? AND a.artist_name = ?
            """, (title, date, artist_name))
            if cursor.fetchone():
                confirm_btn.config(state="disabled")
                validation_label.config(text="A performance with this artist, title, and date already exists.")
                return
            confirm_btn.config(state="normal")
            validation_label.config(text="")
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=20)
        def on_confirm():
            try:
                # Pass source_type="url"
                self.confirm_and_save_entry("performance", source_type="url")
                popup.destroy()
            except Exception as e:
                messagebox.showerror("Database Error", f"Failed to save entry: {e}", parent=self)
        confirm_btn = ttk.Button(btn_frame, text="Confirm", state="disabled", command=on_confirm)
        confirm_btn.pack(side=tk.LEFT, padx=5)
        cancel_btn = ttk.Button(btn_frame, text="Cancel", command=popup.destroy)
        cancel_btn.pack(side=tk.LEFT, padx=5)
        validate_confirm_state()

    def _build_common_entry_details_ui(self, parent_frame):
        """Builds the common UI elements for data entry (artist, songs, title, date, etc.)."""
        entry_type = self.entry_type_var.get()

        # ARTIST SECTION
        artist_frame = ttk.Frame(parent_frame, style="DataEntry.TFrame")
        artist_frame.pack(fill="x", pady=6)

        ttk.Label(artist_frame, text="Primary Artist:", style="DataEntry.TLabel").grid(row=0, column=0, sticky="w", pady=2, padx=2)
        artist_entry = ttk.Entry(
            artist_frame, textvariable=self.primary_artist_var, width=30, font=FONT_MAIN, style="DataEntry.TEntry", state="readonly"
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
        
        if self.secondary_artist_var.get():
            ttk.Label(artist_frame, text="Secondary Artist:", style="DataEntry.TLabel").grid(row=2, column=0, sticky="w", pady=2, padx=2)
            secondary_entry = ttk.Entry(
                artist_frame, textvariable=self.secondary_artist_var, width=30, font=FONT_MAIN, style="DataEntry.TEntry", state="readonly"
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
        song_frame = ttk.Frame(parent_frame, style="DataEntry.TFrame")
        song_frame.pack(fill="x", pady=(10,0))
        ttk.Label(song_frame, text="Song(s):", style="DataEntry.TLabel").grid(row=0, column=0, sticky="w", pady=2, padx=2)
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

        # TITLE FRAME
        title_frame = ttk.Frame(parent_frame, style="DataEntry.TFrame")
        title_frame.pack(fill="x", pady=(10,0))
        ttk.Label(title_frame, text="Title:", style="DataEntry.TLabel").grid(row=0, column=0, sticky="w", pady=2, padx=2)
        title_entry = ttk.Entry(title_frame, textvariable=self.title_var, width=70, font=FONT_MAIN, style="DataEntry.TEntry")
        title_entry.grid(row=0, column=1, sticky="ew", pady=2, padx=(2,0))
        self._add_right_click_paste(title_entry)
        title_frame.columnconfigure(1, weight=1)

        # DATE ENTRY SECTION
        date_frame = ttk.Frame(parent_frame, style="DataEntry.TFrame")
        date_frame.pack(fill="x", pady=(10,0))
        ttk.Label(date_frame, text="Date (YYMMDD):", style="DataEntry.TLabel").grid(row=0, column=0, sticky="w", pady=2, padx=2)
        if not self.date_var.get(): # Initialize if empty
            self.date_var.set("") 
        self.date_entry = ttk.Entry(date_frame, textvariable=self.date_var, width=12, font=FONT_MAIN, style="DataEntry.TEntry")
        self.date_entry.grid(row=0, column=1, sticky="w", pady=2, padx=(2,0))
        self._add_right_click_paste(self.date_entry)
        ttk.Label(date_frame, text="(e.g. 240530)", style="DataEntry.TLabel").grid(row=0, column=2, sticky="w", padx=(8,2))

        # SHOW TYPE AND RESOLUTION
        if entry_type == "performance":
            showtype_frame = ttk.Frame(parent_frame, style="DataEntry.TFrame")
            showtype_frame.pack(fill="x", pady=(10,0))
            ttk.Label(showtype_frame, text="Show Type:", style="DataEntry.TLabel").grid(row=0, column=0, sticky="w", pady=2, padx=2)
            if not hasattr(self, 'show_type_var'):
                self.show_type_var = tk.StringVar()
            showtype_combo = ttk.Combobox(showtype_frame, textvariable=self.show_type_var, values=self.show_type_choices + ["<Add new>"] if self.show_type_choices else ["<Add new>"], state="readonly", style="DataEntry.TCombobox", width=30)
            showtype_combo.grid(row=0, column=1, sticky="w", pady=2, padx=(2,0))
            def on_showtype_select(event=None):
                if self.show_type_var.get() == "<Add new>":
                    new_val = tk.simpledialog.askstring("Add Show Type", "Enter new show type:", parent=self)
                    if new_val:
                        if new_val not in self.show_type_choices:
                            self.show_type_choices.append(new_val)
                            self.show_type_choices.sort(key=lambda s: s.lower())
                        showtype_combo['values'] = self.show_type_choices + ["<Add new>"]
                        self.show_type_var.set(new_val)
            showtype_combo.bind("<<ComboboxSelected>>", on_showtype_select)

        # RESOLUTION (for both performances and music videos)
        resolution_frame = ttk.Frame(parent_frame, style="DataEntry.TFrame")
        resolution_frame.pack(fill="x", pady=(10,0))
        ttk.Label(resolution_frame, text="Resolution:", style="DataEntry.TLabel").grid(row=0, column=0, sticky="w", pady=2, padx=2)
        if not hasattr(self, 'resolution_var'):
            self.resolution_var = tk.StringVar()
        resolution_combo = ttk.Combobox(resolution_frame, textvariable=self.resolution_var, values=self.resolution_choices + ["<Add new>"] if self.resolution_choices else ["<Add new>"], state="readonly", style="DataEntry.TCombobox", width=30)
        resolution_combo.grid(row=0, column=1, sticky="w", pady=2, padx=(2,0))
        def on_resolution_select(event=None):
            if self.resolution_var.get() == "<Add new>":
                new_val = tk.simpledialog.askstring("Add Resolution", "Enter new resolution:", parent=self)
                if new_val:
                    if new_val not in self.resolution_choices:
                        self.resolution_choices.append(new_val)
                        self.resolution_choices.sort(key=lambda s: s.lower())
                    resolution_combo['values'] = self.resolution_choices + ["<Add new>"]
                    self.resolution_var.set(new_val)
        resolution_combo.bind("<<ComboboxSelected>>", on_resolution_select)

    def handle_proceed(self):
        entry_type = self.entry_type_var.get()
        source_type = self.source_type_var.get()
        
        for widget in self.content_area_frame.winfo_children():
            widget.destroy()
        
        print(f"Proceeding with: Entry={entry_type}, Source={source_type}") # Keep for console feedback

        # Hide Proceed button, show Save Entry button
        self.proceed_button.pack_forget()
        self.save_entry_button.pack(side=tk.RIGHT, padx=5)
        self.cancel_button.pack_forget()
        self.cancel_button.pack(side=tk.RIGHT, padx=5)

        if source_type == "url":
            item_name_display = entry_type.replace('_', ' ').title()
            self.build_url_entry_ui(item_name=item_name_display)
            self.save_entry_button.config(command=lambda: self.confirm_and_save_entry(entry_type, source_type="url"))
            self.save_entry_button.pack(side=tk.RIGHT, padx=5)
            self.cancel_button.pack(side=tk.RIGHT, padx=5)
            self.proceed_button.pack_forget()
            self.proceed_button.config(state=tk.DISABLED)
            if entry_type == "music_video":
                if self._all_mv_url_fields_filled():
                    self._show_mv_url_confirmation_popup()
            elif entry_type == "performance":
                if self._all_performance_url_fields_filled():
                    self._show_performance_url_confirmation_popup()
            return # Done with URL processing

        elif source_type == "local_file":
            item_name_display = entry_type.replace('_', ' ').title()
            self.build_local_file_entry_ui(item_name=item_name_display)
            self.save_entry_button.config(command=self._attempt_save_local_entry)
            self.save_entry_button.pack(side=tk.RIGHT, padx=5)
            self.cancel_button.pack(side=tk.RIGHT, padx=5)
            self.proceed_button.pack_forget()
            self.proceed_button.config(state=tk.DISABLED)
            return # Done with local file UI setup

        # Fallback for any unhandled combination (should ideally not be reached
        # if entry_type and source_type are always one of the handled values)
        else:
            ttk.Label(self.content_area_frame,
                      text=f"Unhandled Selection:\nEntry Type: {entry_type.replace('_', ' ').title()}\nSource Type: {source_type.replace('_', ' ').title()}",
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

    def _add_right_click_paste(self, entry_widget):
        """Attach a right-click context menu with Paste to the given Entry widget."""
        menu = tk.Menu(entry_widget, tearoff=0)
        menu.add_command(label="Paste", command=lambda: entry_widget.event_generate('<<Paste>>'))
        def show_menu(event):
            menu.tk_popup(event.x_root, event.y_root)
        entry_widget.bind("<Button-3>", show_menu)

    def _convert_yymmdd_to_yyyy_mm_dd(self, yymmdd):
        """Convert YYMMDD string to YYYY-MM-DD or return None if invalid."""
        try:
            dt = datetime.datetime.strptime(yymmdd, "%y%m%d")
            return dt.strftime("%Y-%m-%d")
        except Exception:
            return None
    
    def _show_custom_file_dialog(self, initialdir, filetypes):
        """Stubbed legacy custom dialog; now delegates to utils.show_file_browser"""
        return utils.show_file_browser(self, initialdir, filetypes)

    def build_url_entry_ui(self, item_name):
        # content_area_frame is already cleared by handle_proceed
        step_frame = ttk.Frame(self.content_area_frame, style="DataEntry.TFrame")
        step_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- URL Specific Section ---
        url_frame = ttk.LabelFrame(step_frame, text=f"A. Enter {item_name} URL", style="DataEntry.TFrame", padding=10)
        url_frame.pack(fill="x", pady=5, anchor="n")

        ttk.Label(url_frame, text="URL:", style="DataEntry.TLabel").pack(anchor="w", pady=(0,2))
        url_entry = ttk.Entry(url_frame, textvariable=self.url_entry_var, width=70, font=FONT_MAIN, style="DataEntry.TEntry")
        url_entry.pack(fill="x", pady=(0,5))
        self._add_right_click_paste(url_entry)
        self.after(100, lambda: url_entry.focus_set()) # Focus URL entry

        go_button = ttk.Button(url_frame, text="GO", command=self.open_url_in_browser, style="DataEntry.TButton")
        go_button.pack(anchor="e", pady=2)

        # --- Common Details Section ---
        details_frame = ttk.LabelFrame(step_frame, text="B. Enter Details", style="DataEntry.TFrame", padding=10)
        details_frame.pack(fill="x", pady=10, anchor="n")
        self._build_common_entry_details_ui(details_frame)


    def build_local_file_entry_ui(self, item_name):
        """Builds the UI for selecting local files and entering their details."""
        # content_area_frame is already cleared by handle_proceed
        
        step_frame = ttk.Frame(self.content_area_frame, style="DataEntry.TFrame")
        step_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- Section for File Selection ---
        file_selection_frame = ttk.Frame(step_frame, style="DataEntry.TFrame")
        file_selection_frame.pack(fill="x", pady=(10, 0), anchor="n")

        # Large, styled section label
        file_section_label = tk.Label(
            file_selection_frame, text="Select File", font=("Arial", 18, "bold"),
            bg=DARK_BG, fg=BRIGHT_FG, pady=8, anchor="w"
        )
        file_section_label.pack(fill="x", padx=2, pady=(0, 8))

        # File action buttons
        button_row = ttk.Frame(file_selection_frame, style="DataEntry.TFrame")
        button_row.pack(fill="x", pady=(0, 0))
        browse_button = ttk.Button(button_row, text="Browse File", command=self.browse_local_files, style="DataEntry.TButton")
        browse_button.pack(side=tk.LEFT, pady=(0,2), padx=(2, 2))
        self.play_button = ttk.Button(button_row, text="Play File", command=self.play_selected_file, style="DataEntry.TButton", state=tk.DISABLED)
        self.play_button.pack(side=tk.LEFT, padx=(8,2), pady=(0,2))

        # File path entry directly below buttons
        selected_files_entry = ttk.Entry(file_selection_frame, textvariable=self.local_files_display_var, width=80, font=FONT_MAIN, style="DataEntry.TEntry", state='readonly')
        selected_files_entry.pack(fill="x", padx=2, pady=(6, 10))

        # --- Common Details Section ---
        details_section_label = tk.Label(
            step_frame, text="Enter Details", font=("Arial", 18, "bold"),
            bg=DARK_BG, fg=BRIGHT_FG, pady=8, anchor="w"
        )
        details_section_label.pack(fill="x", padx=2, pady=(10, 8))
        details_frame = ttk.Frame(step_frame, style="DataEntry.TFrame")
        details_frame.pack(fill="x", pady=(0, 10), anchor="n")
        self._build_common_entry_details_ui(details_frame)

        # --- Validation Message Label ---
        validation_label = ttk.Label(step_frame, textvariable=self.local_file_validation_label_var, foreground="red", style="DataEntry.TLabel", wraplength=700)
        validation_label.pack(pady=(5,0), anchor="w", padx=10)

    def _validate_local_file_data(self):
        """Validates the data entered for a local file entry."""
        self.local_file_validation_label_var.set("") # Clear previous messages
        errors = []

        # Must have exactly one local file selected
        if len(self.selected_local_files) != 1:
            errors.append("- Exactly one local file must be selected.")
        
        if not self.primary_artist_var.get().strip():
            errors.append("- Primary Artist must be selected.")
        
        # Songs are optional for MVs, potentially optional for performances too,
        # but title is usually derived or entered.
        # if not self.selected_song_titles:
        #     errors.append("- At least one Song must be selected.")

        if not self.title_var.get().strip():
            errors.append("- Title must be entered.")

        date_str = self.date_var.get().strip()
        if not date_str:
            errors.append("- Date must be entered.")
        elif not (date_str.isdigit() and len(date_str) == 6):
            errors.append("- Date must be in YYMMDD format (e.g., 240531).")

        entry_type = self.entry_type_var.get()
        if entry_type == "performance":
            if hasattr(self, 'show_type_var'):
                show_type = self.show_type_var.get().strip()
                if not show_type or show_type == "<Add new>":
                    errors.append("- Show Type must be selected or entered.")
            else: # Should not happen if UI built correctly
                errors.append("- Show Type field is missing.")
            
            if hasattr(self, 'resolution_var'):
                resolution = self.resolution_var.get().strip()
                if not resolution or resolution == "<Add new>":
                    errors.append("- Resolution must be selected or entered.")
            else: # Should not happen
                errors.append("- Resolution field is missing.")

        if errors:
            self.local_file_validation_label_var.set("Please correct the following errors:\n" + "\n".join(errors))
            return False
        return True

    def _attempt_save_local_entry(self):
        """Attempts to save the local file entry after validation."""
        if self._validate_local_file_data():
            self.local_file_validation_label_var.set("") # Clear validation message on success
            entry_type = self.entry_type_var.get()
            # Prepare data and insert into DB for local file entries
            raw_date = self.date_var.get().strip()
            formatted_date = self._convert_yymmdd_to_yyyy_mm_dd(raw_date)
            perf_date = formatted_date if formatted_date else raw_date
            # Build artist names list
            artist_names = [self.primary_artist_var.get().strip()] + ([self.secondary_artist_var.get().strip()] if self.secondary_artist_var.get().strip() else [])
            song_titles = self.selected_song_titles

            # Insert record based on entry type
            if entry_type == "performance":
                show_type = self.show_type_var.get().strip()
                resolution = self.resolution_var.get().strip()
                self.db_ops.insert_performance(title=self.title_var.get().strip(), performance_date=perf_date,
                                               show_type=show_type, resolution=resolution,
                                               file_path1=self.selected_local_files[0], file_url=None,
                                               score=0, artist_names=artist_names,
                                               song_titles=song_titles)
                messagebox.showinfo("Saved", f"Performance '{self.title_var.get().strip()}' saved successfully.", parent=self)
                # Refresh main window list
                self.master_app.load_performances()
                self.master_app.update_list()
                # Reset form for next entry instead of closing window
                self.reset_form_fields()
                return
            else:
                resolution = self.resolution_var.get().strip() if hasattr(self, 'resolution_var') else ''
                self.db_ops.insert_music_video(title=self.title_var.get().strip(), release_date=perf_date,
                                               resolution=resolution if resolution else None, file_path1=self.selected_local_files[0], file_url=None,
                                               score=0, artist_names=artist_names,
                                               song_titles=song_titles)
                messagebox.showinfo("Saved", f"Music Video '{self.title_var.get().strip()}' saved successfully.", parent=self)
                # Refresh main window list
                self.master_app.load_performances()
                self.master_app.update_list()
                # Reset form for next entry instead of closing window
                self.reset_form_fields()
                return

        # If validation fails, the message is already set by _validate_local_file_data

    def browse_local_files(self):
        """Opens a file dialog to select local media files and updates the display."""
        filetypes = (
            ('Media files', '*.mp4 *.mkv *.avi *.mov *.webm *.flv *.wmv *.ts *.tp *.mp3 *.wav *.flac *.aac *.ogg'),
            ('Video files', '*.mp4 *.mkv *.avi *.mov *.webm *.flv *.wmv *.ts *.tp'),
            ('Audio files', '*.mp3 *.wav *.flac *.aac *.ogg'),
            ('All files', '*.*')
        )
        
        # Determine last used directory from user home store
        store_path = os.path.expanduser('~/.kpop_last_dir.txt')
        initial_dir = None
        try:
            with open(store_path, 'r') as sf:
                last = sf.read().strip()
                if last and os.path.isdir(last):
                    initial_dir = last
        except Exception:
            pass
        # Try custom file browser for larger browsing window; fallback to native only if error
        try:
            filename = utils.show_file_browser(self, initial_dir, filetypes)
        except Exception:
            filename = filedialog.askopenfilename(
                title='Select Local Media File',
                filetypes=filetypes,
                parent=self,
                initialdir=initial_dir
            )
        # Only one file allowed
        if filename:
            # Save directory for next time
            try:
                with open(store_path, 'w') as sf:
                    sf.write(os.path.dirname(filename))
            except Exception:
                pass
                
            self.selected_local_files = [filename]
            self.local_files_display_var.set(f"Selected: {filename}")
            
            # Try to extract date from filename and prefill the date box
            date_from_filename = utils.extract_date_from_filepath(filename)
            if date_from_filename:
                self.date_var.set(date_from_filename)
            
            # Try to find artist name in the filename and prefill the primary artist field
            if self.all_artists_list:
                # Use the enhanced artist detection function with detailed results
                result = utils.find_artist_in_filename(filename, self.all_artists_list, detailed=True)
                
                if result:
                    best_artist_match, score, match_type = result
                    
                    # Use the best match if it meets our confidence threshold
                    if score >= 60:  # High confidence match
                        self.primary_artist_var.set(best_artist_match['name'])
                        
                        # After setting the artist, try to detect and select songs
                        self.detect_and_prefill_songs_from_filename(filename)
                    else:
                        # Fall back to the simple string matching function for low confidence matches
                        artist_names = [artist['name'] for artist in self.all_artists_list]
                        found_artists = utils.find_string_in_filename(filename, artist_names)
                        
                        # If we found any artists, use the first one (highest confidence match)
                        if found_artists:
                            self.primary_artist_var.set(found_artists[0])
                            
                            # After setting the artist, try to detect and select songs
                            self.detect_and_prefill_songs_from_filename(filename)
                            
                            # If we found multiple artists, show a message about other potential matches
                            if len(found_artists) > 1:
                                other_artists = ", ".join(found_artists[1:3])  # Show up to 2 additional matches
                                additional = len(found_artists) - 3
                                if additional > 0:
                                    other_artists += f" and {additional} more"
                                print(f"Multiple artists matched: Selected {found_artists[0]}. Other potential matches: {other_artists}")
                else:
                    # No artists detected in filename
                    pass
                
            # Enable play button when a file is selected
            if hasattr(self, 'play_button'):
                self.play_button.config(state=tk.NORMAL)
        else:
            self.selected_local_files = []
            self.local_file_validation_label_var.set("")
            self.local_files_display_var.set("No files selected.")
            # Disable play button when no file is selected
            if hasattr(self, 'play_button'):
                self.play_button.config(state=tk.DISABLED)

    def confirm_and_save_entry(self, entry_type, source_type="url"): # Added source_type
        print(f"Attempting to save: Entry Type='{entry_type}', Source Type='{source_type}'")

        if source_type == "url":
            # Gather URL entry details
            url = self.url_entry_var.get().strip()
            primary_artist = self.primary_artist_var.get().strip()
            secondary_artist = None
            if hasattr(self, 'secondary_artist_var') and self.secondary_artist_var.get().strip():
                secondary_artist = self.secondary_artist_var.get().strip()
            song_titles = self.selected_song_titles
            title = self.title_var.get().strip()
            raw_date = self.date_var.get().strip()
            formatted_date = self._convert_yymmdd_to_yyyy_mm_dd(raw_date)
            perf_date = formatted_date if formatted_date else raw_date
            artist_names = [primary_artist] + ([secondary_artist] if secondary_artist else [])
            try:
                if entry_type == "music_video":
                    # Insert Music Video record
                    self.db_ops.insert_music_video(
                        resolution=None,
                        title=title,
                        release_date=perf_date,
                        file_path1=None,
                        file_url=url,
                        score=0,
                        artist_names=artist_names,
                        song_titles=song_titles
                    )
                    messagebox.showinfo("Saved", f"Music Video '{title}' saved successfully.", parent=self)
                elif entry_type == "performance":
                    # Insert Performance record
                    show_type = self.show_type_var.get().strip() if hasattr(self, 'show_type_var') else ''
                    resolution = self.resolution_var.get().strip() if hasattr(self, 'resolution_var') else ''
                    self.db_ops.insert_performance(
                        title=title,
                        performance_date=perf_date,
                        show_type=show_type,
                        resolution=resolution,
                        file_path1=None,
                        file_url=url,
                        score=0,
                        artist_names=artist_names,
                        song_titles=song_titles
                    )
                    messagebox.showinfo("Saved", f"Performance '{title}' saved successfully.", parent=self)
                # Refresh main window data and reset form
                self.master_app.load_performances()
                self.master_app.update_list()
                self.reset_form_fields()
            except Exception as e:
                messagebox.showerror("Database Error", f"Failed to save entry: {e}", parent=self)
            return
        elif source_type == "local_file":
            # Placeholder for single local file saving logic
            primary_artist = self.primary_artist_var.get().strip()
            secondary_artist = self.secondary_artist_var.get().strip() if hasattr(self, 'secondary_artist_var') and self.secondary_artist_var.get() else None
            song_titles = self.selected_song_titles
            title = self.title_var.get().strip()
            date_yyyymmdd = self.date_var.get().strip()  # Assuming YYMMDD
            # Only support one selected file
            file_path1 = self.selected_local_files[0] if self.selected_local_files else None

            # --- DB-duplication checks ---
            conn = self.db_ops.get_db_connection()
            cursor = conn.cursor()
            #  1. Ensure selected file is not already in DB
            if file_path1:
                table = 'performances' if entry_type == 'performance' else 'music_videos'
                query = f"SELECT 1 FROM {table} WHERE file_path1 = ?"
                cursor.execute(query, (file_path1,))
                if cursor.fetchone():
                    messagebox.showerror("Duplicate File", f"The file '{file_path1}' is already in the database.", parent=self)
                    return
            # 2. Ensure no existing entry with same artist+title(+date)
            if entry_type == 'performance':
                cursor.execute(
                    """
                    SELECT 1 FROM performances p
                    JOIN performance_artist_link pal ON p.performance_id = pal.performance_id
                    JOIN artists a ON pal.artist_id = a.artist_id
                    WHERE p.title = ? AND p.performance_date = ? AND a.artist_name = ?
                    """, (title, date_yyyymmdd, primary_artist)
                )
            else:
                cursor.execute(
                    """
                    SELECT 1 FROM music_videos mv
                    JOIN music_video_artist_link mval ON mv.mv_id = mval.mv_id
                    JOIN artists a ON mval.artist_id = a.artist_id
                    WHERE mv.title = ? AND a.artist_name = ?
                    """, (title, primary_artist)
                )
            if cursor.fetchone():
                label = 'Performance' if entry_type == 'performance' else 'Music Video'
                msg = f"A {label.lower} with the same artist, title{', and date' if entry_type == 'performance' else ''} already exists."
                messagebox.showerror("Duplicate Entry", msg, parent=self)
                return

            # Prepare data and insert into DB for local file entries
            raw_date = date_yyyymmdd
            formatted_date = self._convert_yymmdd_to_yyyy_mm_dd(raw_date)
            perf_date = formatted_date if formatted_date else raw_date
            # Build artist names list
            artist_names = [primary_artist] + ([secondary_artist] if secondary_artist else [])
            # Insert record based on entry type
            if entry_type == "performance":
                show_type = self.show_type_var.get().strip()
                resolution = self.resolution_var.get().strip()
                self.db_ops.insert_performance(title=title, performance_date=perf_date,
                                               show_type=show_type, resolution=resolution,
                                               file_path1=file_path1, file_url=None,
                                               score=0, artist_names=artist_names,
                                               song_titles=song_titles)
                messagebox.showinfo("Saved", f"Performance '{title}' saved successfully.", parent=self)
                # Refresh main window list
                self.master_app.load_performances()
                self.master_app.update_list()
                # Reset form for next entry instead of closing window
                self.reset_form_fields()
                return
            else:
                self.db_ops.insert_music_video(title=title, release_date=perf_date,
                                               resolution=None,
                                               file_path1=file_path1, file_url=None,
                                               score=0, artist_names=artist_names,
                                               song_titles=song_titles)
                messagebox.showinfo("Saved", f"Music Video '{title}' saved successfully.", parent=self)
                # Refresh main window list
                self.master_app.load_performances()
                self.master_app.update_list()
                # Reset form for next entry instead of closing window
                self.reset_form_fields()
                return

        else:
            messagebox.showerror("Error", f"Unknown source type: {source_type}", parent=self)
            return

        # Common actions after save attempt (success or placeholder)
        # Potentially reset common fields if save was successful
        # self.reset_form_fields() # Or handle reset based on source_type success

    def update_artists_from_spotify(self):
        # Call the unified sync script in the main project directory
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            update_script = os.path.join(base_dir, "spotify_update_from.py")
            subprocess.run([sys.executable, update_script], check=True)
            self.load_initial_data()
            messagebox.showinfo("Artists Updated", "Artists have been updated and enriched from Spotify.", parent=self)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update artists from Spotify:\n{e}", parent=self)

    def add_secondary_artist_placeholder(self):
        # Set a placeholder so the secondary artist field appears
        self.secondary_artist_var.set("Select...") # Or some other indicator
        self.handle_proceed() # Rebuild current UI

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
                self.secondary_artist_var.set(artist_name)
                popup.destroy()
                self.handle_proceed() # Rebuild current UI

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
        self.handle_proceed() # Rebuild current UI

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
            # self.build_url_entry_ui(item_name="Performance" if self.entry_type_var.get() == "performance" else "Music Video")
            self.handle_proceed() # Rebuild current UI
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

    def detect_and_prefill_songs_from_filename(self, filename):
        """
        Try to detect songs in the filename based on the selected artist and prefill the song selection.
        This method should be called after setting the primary artist.
        """
        if not filename or not self.primary_artist_var.get():
            return
            
        # First, get all songs for the selected artist
        songs = self.get_songs_for_selected_artists()
        if not songs:
            print("No songs found for the selected artist")
            return
            
        # Use our utility function to find song matches in the filename
        song_matches = utils.find_song_in_filename(filename, songs, detailed=True)
        
        if not song_matches:
            print("No song matches found in filename")
            return
            
        # Process the matches to select songs
        high_confidence_matches = [match for match in song_matches if match[2] >= 70]  # Score >= 70
        
        # Clear existing song selections
        self.selected_song_ids = []
        self.selected_song_titles = []
        
        # Add high confidence matches first
        selected_titles = set()  # Use a set to avoid duplicates
        for song_id, song_title, score, match_type in high_confidence_matches[:3]:  # Limit to top 3
            if song_title not in selected_titles:  # Avoid duplicates
                self.selected_song_ids.append(song_id)
                self.selected_song_titles.append(song_title)
                selected_titles.add(song_title)
                print(f"Auto-selected song: {song_title} (Score: {score:.1f}, Type: {match_type})")
        
        # If no high confidence matches, try low confidence matches
        if not selected_titles:
            low_confidence_matches = [match for match in song_matches if match[2] < 70 and match[2] >= 50]  # Score 50-69
            for song_id, song_title, score, match_type in low_confidence_matches[:2]:  # Limit to top 2
                if song_title not in selected_titles:  # Avoid duplicates
                    self.selected_song_ids.append(song_id)
                    self.selected_song_titles.append(song_title)
                    selected_titles.add(song_title)
                    print(f"Auto-selected song (low confidence): {song_title} (Score: {score:.1f}, Type: {match_type})")
        
        # If we found songs, update the title and refresh the UI
        if selected_titles:
            print(f"Auto-detected {len(selected_titles)} song(s) from filename")
            # Update the title field with the detected songs
            self.update_title_from_songs()
            # Refresh the UI to show the selected songs
            self.handle_proceed()
        else:
            print("No song matches found in filename")

    def remove_selected_song(self, idx):
        title_to_remove = self.selected_song_titles[idx]
        
        # Remove all song_ids associated with this title from self.selected_song_ids
        # This requires knowing which song_ids map to which title, or a more careful removal.
        # For simplicity, if multiple songs can have the same title but different IDs,
        # this current approach might remove more IDs than intended if not careful.
        # Assuming for now that selected_song_titles and selected_song_ids are kept in sync
        # such that removing by index is safe. If a title can map to multiple selected IDs,
        # this needs refinement.
        
        del self.selected_song_titles[idx]
        # This part is tricky if a title can have multiple IDs.
        # If self.selected_song_ids contains ALL ids for ALL selected titles,
        # removing just one ID by index might be wrong.
        # The `on_ok` in `show_song_selection_popup` does:
        # selected_song_ids = []
        # for title in selected_titles:
        #    selected_song_ids.extend(title_to_song_ids[title])
        # This means self.selected_song_ids can be longer.
        # Safest for now:
        self.selected_song_ids = [] # Force re-selection or clear
        # This will make the "Title" not auto-update correctly from songs if songs are removed one by one.

        self.handle_proceed() # Rebuild current UI
        self.update_title_from_songs()


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

    def confirm_and_save_entry(self, entry_type, source_type="url"): # Added source_type
        print(f"Attempting to save: Entry Type='{entry_type}', Source Type='{source_type}'")

        if source_type == "url":
            # Gather URL entry details
            url = self.url_entry_var.get().strip()
            primary_artist = self.primary_artist_var.get().strip()
            secondary_artist = None
            if hasattr(self, 'secondary_artist_var') and self.secondary_artist_var.get().strip():
                secondary_artist = self.secondary_artist_var.get().strip()
            song_titles = self.selected_song_titles
            title = self.title_var.get().strip()
            raw_date = self.date_var.get().strip()
            formatted_date = self._convert_yymmdd_to_yyyy_mm_dd(raw_date)
            perf_date = formatted_date if formatted_date else raw_date
            artist_names = [primary_artist] + ([secondary_artist] if secondary_artist else [])
            try:
                if entry_type == "music_video":
                    # Insert Music Video record
                    resolution = self.resolution_var.get().strip() if hasattr(self, 'resolution_var') else ''
                    self.db_ops.insert_music_video(
                        title=title,
                        release_date=perf_date,
                        resolution=resolution if resolution else None,
                        file_path1=None,
                        file_url=url,
                        score=0,
                        artist_names=artist_names,
                        song_titles=song_titles
                    )
                    messagebox.showinfo("Saved", f"Music Video '{title}' saved successfully.", parent=self)
                elif entry_type == "performance":
                    # Insert Performance record
                    show_type = self.show_type_var.get().strip() if hasattr(self, 'show_type_var') else ''
                    resolution = self.resolution_var.get().strip() if hasattr(self, 'resolution_var') else ''
                    self.db_ops.insert_performance(
                        title=title,
                        performance_date=perf_date,
                        show_type=show_type,
                        resolution=resolution,
                        file_path1=None,
                        file_url=url,
                        score=0,
                        artist_names=artist_names,
                        song_titles=song_titles
                    )
                    messagebox.showinfo("Saved", f"Performance '{title}' saved successfully.", parent=self)
                # Refresh main window data and reset form
                self.master_app.load_performances()
                self.master_app.update_list()
                self.reset_form_fields()
            except Exception as e:
                messagebox.showerror("Database Error", f"Failed to save entry: {e}", parent=self)
            return
        elif source_type == "local_file":
            # Placeholder for single local file saving logic
            primary_artist = self.primary_artist_var.get().strip()
            secondary_artist = self.secondary_artist_var.get().strip() if hasattr(self, 'secondary_artist_var') and self.secondary_artist_var.get() else None
            song_titles = self.selected_song_titles
            title = self.title_var.get().strip()
            date_yyyymmdd = self.date_var.get().strip()  # Assuming YYMMDD
            # Only support one selected file
            file_path1 = self.selected_local_files[0] if self.selected_local_files else None

            # --- DB-duplication checks ---
            conn = self.db_ops.get_db_connection()
            cursor = conn.cursor()
            #  1. Ensure selected file is not already in DB
            if file_path1:
                table = 'performances' if entry_type == 'performance' else 'music_videos'
                query = f"SELECT 1 FROM {table} WHERE file_path1 = ?"
                cursor.execute(query, (file_path1,))
                if cursor.fetchone():
                    messagebox.showerror("Duplicate File", f"The file '{file_path1}' is already in the database.", parent=self)
                    return
            # 2. Ensure no existing entry with same artist+title(+date)
            if entry_type == 'performance':
                cursor.execute(
                    """
                    SELECT 1 FROM performances p
                    JOIN performance_artist_link pal ON p.performance_id = pal.performance_id
                    JOIN artists a ON pal.artist_id = a.artist_id
                    WHERE p.title = ? AND p.performance_date = ? AND a.artist_name = ?
                    """, (title, date_yyyymmdd, primary_artist)
                )
            else:
                cursor.execute(
                    """
                    SELECT 1 FROM music_videos mv
                    JOIN music_video_artist_link mval ON mv.mv_id = mval.mv_id
                    JOIN artists a ON mval.artist_id = a.artist_id
                    WHERE mv.title = ? AND a.artist_name = ?
                    """, (title, primary_artist)
                )
            if cursor.fetchone():
                label = 'Performance' if entry_type == 'performance' else 'Music Video'
                msg = f"A {label.lower} with the same artist, title{', and date' if entry_type == 'performance' else ''} already exists."
                messagebox.showerror("Duplicate Entry", msg, parent=self)
                return

            # Prepare data and insert into DB for local file entries
            raw_date = date_yyyymmdd
            formatted_date = self._convert_yymmdd_to_yyyy_mm_dd(raw_date)
            perf_date = formatted_date if formatted_date else raw_date
            # Build artist names list
            artist_names = [primary_artist] + ([secondary_artist] if secondary_artist else [])
            # Insert record based on entry type
            if entry_type == "performance":
                show_type = self.show_type_var.get().strip()
                resolution = self.resolution_var.get().strip()
                self.db_ops.insert_performance(title=title, performance_date=perf_date,
                                               show_type=show_type, resolution=resolution,
                                               file_path1=file_path1, file_url=None,
                                               score=0, artist_names=artist_names,
                                               song_titles=song_titles)
                messagebox.showinfo("Saved", f"Performance '{title}' saved successfully.", parent=self)
                # Refresh main window list
                self.master_app.load_performances()
                self.master_app.update_list()
                # Reset form for next entry instead of closing window
                self.reset_form_fields()
                return
            else:
                self.db_ops.insert_music_video(title=title, release_date=perf_date,
                                               resolution=None,
                                               file_path1=file_path1, file_url=None,
                                               score=0, artist_names=artist_names,
                                               song_titles=song_titles)
                messagebox.showinfo("Saved", f"Music Video '{title}' saved successfully.", parent=self)
                # Refresh main window list
                self.master_app.load_performances()
                self.master_app.update_list()
                # Reset form for next entry instead of closing window
                self.reset_form_fields()
                return

        else:
            messagebox.showerror("Error", f"Unknown source type: {source_type}", parent=self)
            return

        # Common actions after save attempt (success or placeholder)
        # Potentially reset common fields if save was successful
        # self.reset_form_fields() # Or handle reset based on source_type success

    def play_selected_file(self):
        """Plays the selected local file using MPV player or webbrowser."""
        if not self.selected_local_files:
            return
        file_path = self.selected_local_files[0]
        try:
            # Warm up drive by reading first byte
            with open(file_path, 'rb') as f:
                f.read(1)
            subprocess.Popen([config.MPV_PLAYER_PATH, '--fs', file_path])
        except Exception as e:
            try:
                webbrowser.open_new(file_path)
            except Exception:
                messagebox.showerror("Playback Error", f"Could not play file: {e}", parent=self)
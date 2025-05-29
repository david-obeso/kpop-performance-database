# data_entry_ui.py
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import sys
import os

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
        self.geometry("900x800")  # Or adjust as needed
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

        button_frame = ttk.Frame(main_frame, style="DataEntry.TFrame")
        button_frame.pack(fill="x", pady=(10, 0), side=tk.BOTTOM)

        self.proceed_button = ttk.Button(button_frame, text="Proceed / Next Step", command=self.handle_proceed, style="DataEntry.TButton")
        self.proceed_button.pack(side=tk.RIGHT, padx=5)

        self.cancel_button = ttk.Button(button_frame, text="Cancel", command=self.close_window, style="DataEntry.TButton")
        self.cancel_button.pack(side=tk.RIGHT, padx=5)
        
        self.protocol("WM_DELETE_WINDOW", self.close_window)
        self.load_initial_data() 
        self.focus_set()

    def load_initial_data(self):
        self.all_artists_list = self.db_ops.get_all_artists()
        # Sort the list of dicts by 'name', case-insensitive
        self.all_artists_list = sorted(self.all_artists_list, key=lambda a: a['name'].lower())

    def reset_content_on_selection_change(self):
        for widget in self.content_area_frame.winfo_children():
            widget.destroy()
        self.current_content_placeholder_label = ttk.Label(self.content_area_frame, text="Selections changed. Click 'Proceed / Next Step'.", style="DataEntry.TLabel")
        self.current_content_placeholder_label.pack(padx=10, pady=20, anchor="center")
        self.url_entry_var.set("")

    def handle_proceed(self):
        entry_type = self.entry_type_var.get()
        source_type = self.source_type_var.get()
        
        for widget in self.content_area_frame.winfo_children():
            widget.destroy()

        print(f"Proceeding with: Entry={entry_type}, Source={source_type}") # Keep for console feedback

        if entry_type == "performance" and source_type == "url":
            self.build_url_entry_ui(item_name="Performance")
        elif entry_type == "music_video" and source_type == "url":
            self.build_url_entry_ui(item_name="Music Video")
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

        check_url_button = ttk.Button(url_frame, text="Check URL", command=self.check_entered_url, style="DataEntry.TButton")
        check_url_button.pack(anchor="e", pady=2)

        artist_frame = ttk.Frame(step_frame, style="DataEntry.TFrame")  # <-- FIXED HERE
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

        ttk.Label(step_frame, text="Next: Song Selection...", style="DataEntry.TLabel").pack(anchor="w", pady=(15,0))

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
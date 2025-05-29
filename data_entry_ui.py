# data_entry_ui.py
import tkinter as tk
from tkinter import ttk, messagebox

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
        self.geometry("700x650") 
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

        artist_frame = ttk.LabelFrame(step_frame, text="B. Select Artist(s)", style="DataEntry.TFrame", padding=10)
        artist_frame.pack(fill="x", pady=10, anchor="n")

        ttk.Label(artist_frame, text="Primary Artist:", style="DataEntry.TLabel").grid(row=0, column=0, sticky="w", pady=2, padx=2)
        
        artist_names_for_combo = [artist['name'] for artist in self.all_artists_list]
        is_artist_list_empty = not bool(artist_names_for_combo)
        
        if is_artist_list_empty:
            current_artist_values = ["No artists in DB"]
            combobox_state = "disabled"
        else:
            current_artist_values = artist_names_for_combo
            combobox_state = "readonly"

        self.primary_artist_combo = ttk.Combobox(artist_frame, textvariable=self.primary_artist_var,
                                                 values=current_artist_values, width=30, style="DataEntry.TCombobox",
                                                 state=combobox_state) 
        self.primary_artist_combo.grid(row=0, column=1, sticky="ew", pady=2, padx=2)
        
        if not is_artist_list_empty:
             self.primary_artist_combo.current(0) 
             self.primary_artist_var.set(self.primary_artist_combo.get()) # Ensure var is set
        else:
            self.primary_artist_var.set("No artists in DB")

        if not is_artist_list_empty: 
            self.primary_artist_combo.bind("<KeyPress>", self.handle_artist_combo_keypress)
        
        artist_frame.columnconfigure(1, weight=1) 

        artist_buttons_frame = ttk.Frame(artist_frame, style="DataEntry.TFrame")
        artist_buttons_frame.grid(row=1, column=0, columnspan=2, pady=(10,5), sticky="ew")

        update_spotify_btn = ttk.Button(artist_buttons_frame, text="Update Artists (Spotify)",
                                        command=self.update_artists_from_spotify, style="DataEntry.TButton")
        update_spotify_btn.pack(side=tk.LEFT, padx=2)

        add_secondary_btn = ttk.Button(artist_buttons_frame, text="Add Secondary Artist",
                                       command=self.add_secondary_artist_placeholder, style="DataEntry.TButton")
        add_secondary_btn.pack(side=tk.LEFT, padx=2)
        
        ttk.Label(step_frame, text="Next: Song Selection...", style="DataEntry.TLabel").pack(anchor="w", pady=(15,0))

    def update_artists_from_spotify(self):
        messagebox.showinfo("Placeholder", "Functionality to update artists from Spotify script will be here.", parent=self)
        # Potential future logic:
        # result = call_spotify_script()
        # if result_indicates_success:
        #     self.load_initial_data() # Reload self.all_artists_list
        #     new_artist_names = [artist['name'] for artist in self.all_artists_list]
        #     is_new_list_empty = not bool(new_artist_names)
        #     if is_new_list_empty:
        #         self.primary_artist_combo['values'] = ["No artists in DB"]
        #         self.primary_artist_combo.state(["disabled"])
        #         self.primary_artist_var.set("No artists in DB")
        #         self.primary_artist_combo.unbind("<KeyPress>")
        #     else:
        #         self.primary_artist_combo['values'] = new_artist_names
        #         self.primary_artist_combo.state(["readonly"]) # Or just "normal"
        #         self.primary_artist_combo.current(0)
        #         self.primary_artist_var.set(self.primary_artist_combo.get())
        #         self.primary_artist_combo.bind("<KeyPress>", self.handle_artist_combo_keypress)


    def add_secondary_artist_placeholder(self):
        messagebox.showinfo("Placeholder", "Functionality to add a secondary artist will be here.", parent=self)

    def check_entered_url(self):
        url = self.url_entry_var.get()
        if not url:
            messagebox.showwarning("Input Required", "Please enter a URL.", parent=self)
            return
        if url.startswith("http://") or url.startswith("https://"):
            messagebox.showinfo("URL Check", f"URL seems valid:\n{url}", parent=self)
        else:
            messagebox.showerror("URL Check", f"URL does not seem valid:\n{url}", parent=self)
        # print(f"Checking URL: {url}") # Keep for console feedback if desired

    def close_window(self):
        if hasattr(self.master_app, 'data_entry_window_instance') and \
           self.master_app.data_entry_window_instance == self:
            self.master_app.data_entry_window_instance = None
        self.destroy()
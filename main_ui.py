# main_ui.py

import os
import subprocess
import sqlite3 # Needed for ScoreEditorWindow's except sqlite3.Error
import sys
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import random
import webbrowser
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

# Modularized imports
import config
import utils
import db_operations
import data_entry_ui # For the new data entry window
import modify_entry_ui  # For the modify-entry window

# Constants
DARK_BG = "#222222"
BRIGHT_FG = "#f8f8f2"
ACCENT = "#44475a"
# Scale factor for UI
UI_SCALE = 1.42
# Scale factor for font size only
FONT_SCALE = 1.5  # 50% larger than original

def scale_font(font_tuple):
    # font_tuple: (family, size, *modifiers)
    family = font_tuple[0]
    size = int(font_tuple[1] * FONT_SCALE)
    modifiers = font_tuple[2:] if len(font_tuple) > 2 else []
    return (family, size, *modifiers)

FONT_MAIN = scale_font(("Courier New", 13))
FONT_HEADER = scale_font(("Courier New", 13, "bold"))
FONT_LABEL_SMALL = scale_font(("Courier New", 11))
FONT_STATUS = scale_font(("Arial", 13))
FONT_BUTTON = scale_font(("Arial", 13, "bold"))

APP_VERSION = "4.0.2 (Data Entry UI - Phase 1, fonts +15%)" # Updated version

class ScoreEditorWindow(tk.Toplevel): # Keep this class definition as it was
    def __init__(self, master, title, performance_details_list_dicts, db_connection, refresh_callback):
        super().__init__(master)
        self.title(title)
        self.geometry(f"{int(950*UI_SCALE)}x{int(720*UI_SCALE)}") 
        self.configure(bg=DARK_BG)
        self.transient(master)
        self.grab_set()

        self.db_conn = db_connection
        self.refresh_callback = refresh_callback
        self.performance_items_data = []

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=DARK_BG)
        style.configure("TLabel", background=DARK_BG, foreground=BRIGHT_FG, font=FONT_MAIN)
        style.configure("ScoreDisplay.TLabel", background=DARK_BG, foreground=BRIGHT_FG, font=FONT_HEADER)
        style.configure("ScoreChangeTitle.TLabel", background=DARK_BG, foreground=BRIGHT_FG, font=FONT_LABEL_SMALL)
        style.configure("TButton", background=ACCENT, foreground=BRIGHT_FG, font=FONT_BUTTON)
        style.map("TButton", background=[("active", "#6272a4"), ("disabled", "#303030")])
        style.configure("Vertical.TScrollbar", troughcolor=DARK_BG, background=ACCENT, arrowcolor=BRIGHT_FG)
        style.map("Vertical.TScrollbar", background=[("active", "#6272a4")])

        main_frame = ttk.Frame(self, style="TFrame")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        header_label = ttk.Label(main_frame, text=f"Editing scores for {len(performance_details_list_dicts)} item(s): (0-5 points)",
                                 font=FONT_HEADER, style="TLabel")
        header_label.pack(pady=(0,10), anchor="w")

        canvas = tk.Canvas(main_frame, bg=DARK_BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview, style="Vertical.TScrollbar")
        self.scrollable_frame = ttk.Frame(canvas, style="TFrame")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas_window = canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _configure_canvas_window(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind("<Configure>", _configure_canvas_window)

        for perf_dict in performance_details_list_dicts:
            perf_id = perf_dict.get("performance_id")
            artists = perf_dict.get("artists_str", "N/A")
            date = perf_dict.get("performance_date", "N/A")
            db_title_val = perf_dict.get("db_title", "N/A") 
            show_type_val = perf_dict.get("show_type", "N/A") 
            original_score = perf_dict.get("score") if perf_dict.get("score") is not None else 0
            
            item_frame = ttk.Frame(self.scrollable_frame, style="TFrame", padding=(5,0,5,5))
            item_frame.pack(fill="x", pady=(0, 10), padx=2)

            text_info_frame = ttk.Frame(item_frame, style="TFrame")
            text_info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 15))
            text_info_frame.columnconfigure(0, weight=0, minsize=90) 
            text_info_frame.columnconfigure(1, weight=1)
            row_idx = 0
            for label_text, value_text, wrap_len in [
                ("Artist(s):", artists, 400), 
                ("Date:", date, 0), 
                ("Title:", db_title_val, 400), 
                ("Show:", show_type_val, 400)
            ]:
                ttk.Label(text_info_frame, text=label_text, style="TLabel").grid(row=row_idx, column=0, sticky="nw", pady=(0,2))
                val_label = ttk.Label(text_info_frame, text=value_text, style="TLabel")
                if wrap_len: val_label.config(wraplength=wrap_len)
                val_label.grid(row=row_idx, column=1, sticky="nw", pady=(0,2))
                row_idx += 1
            
            score_ui_frame = ttk.Frame(item_frame, style="TFrame")
            score_ui_frame.pack(side=tk.RIGHT, anchor='nw', padx=(0,5), pady=(0,0))

            score_change_title_label = ttk.Label(score_ui_frame, text="Score Change", style="ScoreChangeTitle.TLabel")
            score_change_title_label.pack(side=tk.TOP, anchor='center', pady=(0, 3)) 

            controls_actual_frame = ttk.Frame(score_ui_frame, style="TFrame")
            controls_actual_frame.pack(side=tk.TOP)

            score_var = tk.IntVar(value=original_score)

            minus_btn = ttk.Button(controls_actual_frame, text="-", width=3, style="TButton")
            minus_btn.pack(side=tk.LEFT, ipady=1) 

            score_label = ttk.Label(controls_actual_frame, textvariable=score_var, style="ScoreDisplay.TLabel", anchor="center")
            score_label.pack(side=tk.LEFT, padx=8, ipady=1)

            plus_btn = ttk.Button(controls_actual_frame, text="+", width=3, style="TButton")
            plus_btn.pack(side=tk.LEFT, ipady=1)
            
            minus_btn.config(command=lambda sv=score_var, p_btn=plus_btn, m_btn=minus_btn: self.change_score(sv, -1, p_btn, m_btn))
            plus_btn.config(command=lambda sv=score_var, p_btn=plus_btn, m_btn=minus_btn: self.change_score(sv, 1, p_btn, m_btn))

            self.performance_items_data.append({
                "id": perf_id, "original_score": original_score, "score_var": score_var,
                "plus_btn": plus_btn, "minus_btn": minus_btn, "score_label_widget": score_label
            })
            self.update_button_states(score_var.get(), plus_btn, minus_btn)
            score_label.config(text=str(score_var.get())) 

        button_frame = ttk.Frame(self, style="TFrame")
        button_frame.pack(fill="x", pady=(5,10), padx=10, side=tk.BOTTOM)
        ttk.Button(button_frame, text="Save Changes", command=self.save_changes, style="TButton").pack(side=tk.RIGHT, padx=5, ipadx=10, ipady=3)
        ttk.Button(button_frame, text="Cancel", command=self.cancel, style="TButton").pack(side=tk.RIGHT, ipadx=10, ipady=3)
        
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.focus_set()
        self.update_idletasks()

    def change_score(self, score_var, delta, plus_btn, minus_btn):
        current_score = score_var.get()
        new_score = current_score + delta
        if 0 <= new_score <= 5:
            score_var.set(new_score)
        for item_data in self.performance_items_data:
            if item_data["score_var"] == score_var:
                item_data["score_label_widget"].config(text=str(score_var.get()))
                break
        self.update_button_states(score_var.get(), plus_btn, minus_btn)

    def update_button_states(self, score, plus_btn, minus_btn):
        plus_btn.config(state=tk.NORMAL if score < 5 else tk.DISABLED)
        minus_btn.config(state=tk.NORMAL if score > 0 else tk.DISABLED)

    def save_changes(self): 
        updates_made = 0
        if not self.db_conn:
            messagebox.showerror("Database Error", "No database connection available to save scores.", parent=self)
            return
        try:
            cursor = self.db_conn.cursor()
            for item_data in self.performance_items_data:
                if item_data["score_var"].get() != item_data["original_score"]:
                    cursor.execute("UPDATE performances SET score = ? WHERE performance_id = ?", 
                                   (item_data["score_var"].get(), item_data["id"]))
                    updates_made += 1
            if updates_made > 0: 
                self.db_conn.commit()
                messagebox.showinfo("Success", f"{updates_made} score(s) updated.", parent=self)
            else: 
                messagebox.showinfo("No Changes", "No scores were modified.", parent=self)
        except sqlite3.Error as e: 
            self.db_conn.rollback()
            messagebox.showerror("Database Error", f"Failed to update scores: {e}", parent=self)
        finally:
            if self.refresh_callback: 
                self.refresh_callback() 

    def cancel(self):
        if any(item["score_var"].get() != item["original_score"] for item in self.performance_items_data):
            if not messagebox.askyesno("Confirm Cancel", "Unsaved changes. Are you sure you want to cancel?", parent=self):
                return
        self.destroy_and_clear_master_ref()

    def destroy_and_clear_master_ref(self):
        if hasattr(self.master, 'score_editor_window') and self.master.score_editor_window == self:
            self.master.score_editor_window = None
        self.destroy()

def show_startup_error_and_exit(title, message):
    """Helper function to show an error and exit before main GUI starts."""
    error_root = tk.Tk()
    error_root.withdraw()
    messagebox.showerror(title, message, parent=error_root)
    error_root.destroy()
    sys.exit(1)

class KpopDBBrowser(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"K-Pop Performance Database Browser v{APP_VERSION}") 
        # Scale window size
        base_width, base_height = 2560, 1200
        self.geometry(f"{int(base_width*UI_SCALE)}x{int(base_height*UI_SCALE)}")
        self.configure(bg=DARK_BG)

        self.option_add('*TCombobox*Listbox.background', '#333a40') 
        self.option_add('*TCombobox*Listbox.foreground', BRIGHT_FG)
        self.option_add('*TCombobox*Listbox.selectBackground', ACCENT)
        self.option_add('*TCombobox*Listbox.selectForeground', '#f1fa8c')
        self.option_add('*TCombobox*Listbox.font', FONT_MAIN) 
        self.option_add('*TCombobox*Listbox.relief', 'flat')
        self.option_add('*TCombobox*Listbox.borderwidth', 0)
        
        self.all_performances_data = [] 
        self.filtered_performances_data = [] 
        self.artists_list = [] 
        
        # Initialize sorting variables
        self.sort_column = None
        self.sort_ascending = True
        
        self.RESOLUTION_HIGH_QUALITY_KEYWORDS = ["4k", "upscaled", "ai"]
        self.status_var = tk.StringVar(value="Initializing...")
        self.play_button = None; self.play_random_button = None
        self.random_count_var = tk.StringVar(); self.random_count_dropdown = None
        self.change_score_var = tk.BooleanVar(value=False)
        self.score_editor_window = None
        self.data_entry_window_instance = None # For the new data entry window
        self.modify_window = None  # For the modify-entry window

        # --- New variables for filtering ---
        self.show_mv_var = tk.BooleanVar(value=True)
        self.show_perf_var = tk.BooleanVar(value=True)
        self.show_url_only_var = tk.BooleanVar(value=True)
        self.show_local_var = tk.BooleanVar(value=True)  # Local file filter
        self.show_new_var = tk.BooleanVar(value=False)   # New record filter (score 0 or None)

        # Create large checkbox images before widgets that use them
        self.checkbox_unchecked_img, self.checkbox_checked_img = self._create_checkbox_images(size=28, fg=BRIGHT_FG, bg=DARK_BG, accent=ACCENT)

        self.create_widgets()
        self.load_artists() 
        self.load_performances()

    def _create_checkbox_images(self, size=28, fg='#f8f8f2', bg='#222222', accent='#bd93f9'):
        """Create large checked and unchecked images for checkboxes with correct background."""
        from tkinter import PhotoImage
        
        # Unchecked box
        unchecked = PhotoImage(width=size, height=size)
        for x_coord in range(size):
            for y_coord in range(size):
                if x_coord in (0, size-1) or y_coord in (0, size-1): # Outer border
                    unchecked.put(bg, (x_coord, y_coord))
                elif x_coord in (1, size-2) or y_coord in (1, size-2): # Inner border
                    unchecked.put(fg, (x_coord, y_coord))
                else: # Fill
                    unchecked.put(bg, (x_coord, y_coord))

        # Checked box
        checked = PhotoImage(width=size, height=size)
        for x_coord in range(size):
            for y_coord in range(size):
                if x_coord in (0, size-1) or y_coord in (0, size-1): # Outer border
                    checked.put(bg, (x_coord, y_coord))
                elif x_coord in (1, size-2) or y_coord in (1, size-2): # Inner border
                    checked.put(fg, (x_coord, y_coord)) # Keep inner border bright
                else: # Fill - change to accent color
                    checked.put(accent, (x_coord, y_coord)) # Fill with accent color

        # Draw checkmark using fg (BRIGHT_FG) for max contrast on accent fill
        checkmark_color = fg 
        # Using the user's existing checkmark drawing logic
        for i in range(size//2, size-4):
            checked.put(checkmark_color, (i, i))
            checked.put(checkmark_color, (i, i+1))
            checked.put(checkmark_color, (i, i-1))
        for i in range(size//2, size-4):
            checked.put(checkmark_color, (i, size-i-1))
            checked.put(checkmark_color, (i, size-i-2))
            
        return unchecked, checked

    def create_widgets(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=DARK_BG)
        style.configure("TLabel", background=DARK_BG, foreground=BRIGHT_FG, font=FONT_MAIN)
        style.configure("TButton", background=ACCENT, foreground=BRIGHT_FG, font=FONT_BUTTON)
        style.map("TButton", 
                  background=[("active", "#6272a4"), ("disabled", "#303030")],
                  foreground=[("disabled", "#888888")] 
        )
        style.configure("Custom.TCombobox", font=scale_font(("Courier New", 16, "bold")), selectbackground=ACCENT, selectforeground=BRIGHT_FG)
        style.map("Custom.TCombobox",
            fieldbackground=[('readonly', '#333a40'), ('disabled', '#2a2a2a')],
            foreground=[('readonly', BRIGHT_FG), ('disabled', '#777777')],
            background=[('readonly', ACCENT), ('active', '#6272a4'), ('disabled', '#303030')],
            arrowcolor=[('readonly', BRIGHT_FG),('active', BRIGHT_FG),('disabled', '#777777')]
        )
        # Use classic tk.Checkbutton for larger indicator box
        checkbox_font = scale_font(("Courier New", 15))
        # Make checkboxes bigger by increasing padding, font size, and indicator size
        style.configure("TCheckbutton", background=DARK_BG, foreground=BRIGHT_FG, font=checkbox_font)
        style.map("TCheckbutton", indicatorcolor=[('selected', ACCENT), ('!selected', '#555555')], background=[('active', DARK_BG)])
        # Increase indicator size (the tickbox square) for ttk themed widgets
        try:
            style.element_create("LargeIndicator", "image", "::tk::theme::indicatorLarge", border=2, sticky="")
            style.layout("TCheckbutton",
                [('Checkbutton.padding', {'sticky': 'nswe', 'children': [
                    ('Checkbutton.indicator', {'side': 'left', 'sticky': ''}),
                    ('Checkbutton.focus', {'side': 'left', 'sticky': '', 'children': [
                        ('Checkbutton.label', {'sticky': 'nswe'})
                    ]})
                ]})]
            )
        except Exception:
            pass  # If the theme or element is not available, ignore
        style.configure("Vertical.TScrollbar", troughcolor=DARK_BG, background=ACCENT, arrowcolor=BRIGHT_FG)
        style.map("Vertical.TScrollbar", background=[("active", "#6272a4")])
        style.configure("Horizontal.TScrollbar", troughcolor=DARK_BG, background=ACCENT, arrowcolor=BRIGHT_FG)
        style.map("Horizontal.TScrollbar", background=[("active", "#6272a4")])

        filter_frame = ttk.Frame(self); filter_frame.pack(fill="x", padx=10, pady=8)

        ttk.Label(filter_frame, text="Artist:").pack(side="left")
        self.artist_var = tk.StringVar()
        self.artist_dropdown = ttk.Combobox(filter_frame, textvariable=self.artist_var,
                                           state="readonly", style="Custom.TCombobox",
                                           width=int(40*UI_SCALE))
        self.artist_dropdown.pack(side="left", padx=5, ipadx=5, ipady=6)
        self.artist_dropdown.bind("<<ComboboxSelected>>", lambda e: self.update_list(apply_current_sort=True))
        # Enable keyboard navigation: jump to artist starting with typed letter
        self.artist_dropdown.bind("<KeyPress>", self.handle_artist_combo_keypress)
        
        ttk.Label(filter_frame, text="Date (YYYY or YYYY-MM):").pack(side="left", padx=(15,0))
        self.date_var = tk.StringVar()
        date_entry = tk.Entry(filter_frame, textvariable=self.date_var, width=int(10*UI_SCALE), font=FONT_MAIN, bg=DARK_BG, fg=BRIGHT_FG, insertbackground=BRIGHT_FG)
        date_entry.pack(side="left", padx=5, ipadx=5, ipady=3); date_entry.bind("<KeyRelease>", lambda e: self.update_list(apply_current_sort=True))
        
        # 4K filter: checkbox with label on the right
        self.filter_4k_var = tk.BooleanVar(value=False)
        filter_4k_checkbutton = tk.Checkbutton(filter_frame, variable=self.filter_4k_var,
                                               text="4K", command=lambda: self.update_list(apply_current_sort=True),
                                               font=checkbox_font, bg=DARK_BG, fg=BRIGHT_FG, activebackground=DARK_BG, activeforeground=BRIGHT_FG, highlightthickness=0, bd=0, padx=8, pady=4,
                                               image=self.checkbox_unchecked_img, selectimage=self.checkbox_checked_img, indicatoron=False, compound='left')
        filter_4k_checkbutton.pack(side="left", padx=(15, 10))

        # New records only (score 0 or None)
        self.new_checkbox = tk.Checkbutton(filter_frame, text="New", variable=self.show_new_var, 
                                           command=lambda: self.update_list(apply_current_sort=True),
                                           font=checkbox_font, bg=DARK_BG, fg=BRIGHT_FG, activebackground=DARK_BG, activeforeground=BRIGHT_FG, highlightthickness=0, bd=0, padx=8, pady=4,
                                           image=self.checkbox_unchecked_img, selectimage=self.checkbox_checked_img, indicatoron=False, compound='left')
        self.new_checkbox.pack(side="left", padx=(2, 10))
        
        ttk.Label(filter_frame, text="Search:").pack(side="left", padx=(10,0))
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(filter_frame, textvariable=self.search_var, font=FONT_MAIN, bg=DARK_BG, fg=BRIGHT_FG, insertbackground=BRIGHT_FG)
        search_entry.pack(side="left", fill="x", expand=True, padx=5, ipadx=5, ipady=3); search_entry.bind("<KeyRelease>", lambda e: self.update_list(apply_current_sort=True))
        
        ttk.Button(filter_frame, text="Clear", command=self.clear_search).pack(side="left", padx=5, ipadx=8, ipady=3)

        # Create clickable header frame
        header_frame = tk.Frame(self, bg=DARK_BG)
        header_frame.pack(fill="x", padx=10, pady=(5,0))
        
        # Define column widths and names (adjusted for better alignment)
        self.column_info = [
            {"name": "Date", "width": 13, "key": "performance_date"},
            {"name": "Artist(s)", "width": 32, "key": "artists_str"},
            {"name": "Title", "width": 86, "key": "db_title"},
            {"name": "Show Type", "width": 22, "key": "show_type"},
            {"name": "Res", "width": 10, "key": "resolution"},
            {"name": "Score", "width": 6, "key": "score"},
            {"name": "Source", "width": 12, "key": "source"}
        ]
        
        # Create column header labels and track sort state
        self.sort_column = None
        self.sort_ascending = True
        
        # Create clickable headers
        self.header_labels = []  # Keep track of header labels for easier access
        for i, col in enumerate(self.column_info):
            # Create label with underline to indicate it's clickable
            header_label = tk.Label(
                header_frame, 
                text=f"{col['name']:<{col['width']}}", 
                font=FONT_HEADER, 
                anchor="w", 
                bg=DARK_BG, 
                fg=BRIGHT_FG,
                cursor="hand2",  # Hand cursor to indicate clickable
                padx=0,
                relief="flat"  # Will be changed to "raised" when sorted
            )
            header_label.pack(side="left", padx=(0 if i == 0 else 0, 0))
            
            # Store reference to label
            self.header_labels.append(header_label)
            
            # Add separator between columns
            if i < len(self.column_info) - 1:
                separator = tk.Label(header_frame, text="|", font=FONT_HEADER, bg=DARK_BG, fg=BRIGHT_FG)
                separator.pack(side="left", padx=0)
                
            # Bind events
            header_label.bind("<Button-1>", lambda e, col_key=col["key"]: self.sort_list_by(col_key))
            
            # Add hover effect to indicate interactivity
            header_label.bind("<Enter>", lambda e, label=header_label: self._set_header_hover(label, True))
            header_label.bind("<Leave>", lambda e, label=header_label: self._set_header_hover(label, False))

        listbox_frame = tk.Frame(self, bg=DARK_BG); listbox_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.listbox = tk.Listbox(listbox_frame, font=FONT_MAIN, bg=DARK_BG, fg=BRIGHT_FG,
            selectbackground="#44475a", selectforeground="#f1fa8c", highlightbackground=ACCENT, highlightcolor=ACCENT,
            activestyle="none", relief="flat", borderwidth=0, selectmode=tk.EXTENDED,
            height=int(25*UI_SCALE))
        
        vscroll = ttk.Scrollbar(listbox_frame, orient="vertical", style="Vertical.TScrollbar", command=self.listbox.yview) 
        hscroll = ttk.Scrollbar(listbox_frame, orient="horizontal", style="Horizontal.TScrollbar", command=self.listbox.xview)

        self.listbox.configure(yscrollcommand=vscroll.set, xscrollcommand=hscroll.set)

        vscroll.pack(side="right", fill="y")
        hscroll.pack(side="bottom", fill="x")
        self.listbox.pack(side="left", fill="both", expand=True)
        
        self.listbox.bind("<Double-Button-1>", lambda e: self.play_selected())
        # --- Media type filters: MV, Performance, URL, Local ---
        media_filter_frame = ttk.Frame(self)
        media_filter_frame.pack(fill="x", padx=10, pady=(0,5))
        # Pack right-to-left so items appear in order: MV, Performance, URL, Local
        self.local_checkbox = tk.Checkbutton(media_filter_frame, text="Local", variable=self.show_local_var, 
                                         command=lambda: self.update_list(apply_current_sort=True),
                                         font=checkbox_font, bg=DARK_BG, fg=BRIGHT_FG, activebackground=DARK_BG, activeforeground=BRIGHT_FG, 
                                         selectcolor=DARK_BG, 
                                         highlightthickness=0, bd=0, padx=8, pady=4,
                                         image=self.checkbox_unchecked_img, selectimage=self.checkbox_checked_img, indicatoron=False, compound='left')
        self.local_checkbox.pack(side="right", padx=(0,8))
        self.url_checkbox = tk.Checkbutton(media_filter_frame, text="URL", variable=self.show_url_only_var, 
                                           command=lambda: self.update_list(apply_current_sort=True),
                                           font=checkbox_font, bg=DARK_BG, fg=BRIGHT_FG, activebackground=DARK_BG, activeforeground=BRIGHT_FG, 
                                           selectcolor=DARK_BG, 
                                           highlightthickness=0, bd=0, padx=8, pady=4,
                                           image=self.checkbox_unchecked_img, selectimage=self.checkbox_checked_img, indicatoron=False, compound='left')
        self.url_checkbox.pack(side="right", padx=(0,8))
        self.perf_checkbox = tk.Checkbutton(media_filter_frame, text="Performance", variable=self.show_perf_var, 
                                            command=lambda: self.update_list(apply_current_sort=True),
                                            font=checkbox_font, bg=DARK_BG, fg=BRIGHT_FG, activebackground=DARK_BG, activeforeground=BRIGHT_FG, 
                                            selectcolor=DARK_BG, 
                                            highlightthickness=0, bd=0, padx=8, pady=4,
                                            image=self.checkbox_unchecked_img, selectimage=self.checkbox_checked_img, indicatoron=False, compound='left')
        self.perf_checkbox.pack(side="right", padx=(0,8))
        self.mv_checkbox = tk.Checkbutton(media_filter_frame, text="MV", variable=self.show_mv_var, 
                                          command=lambda: self.update_list(apply_current_sort=True),
                                          font=checkbox_font, bg=DARK_BG, fg=BRIGHT_FG, activebackground=DARK_BG, activeforeground=BRIGHT_FG, 
                                          selectcolor=DARK_BG, 
                                          highlightthickness=0, bd=0, padx=8, pady=4,
                                          image=self.checkbox_unchecked_img, selectimage=self.checkbox_checked_img, indicatoron=False, compound='left')
        self.mv_checkbox.pack(side="right", padx=(0,8))

        # Management frame for Add/Modify Data button
        self.management_frame_for_data_entry = ttk.Frame(self)
        self.management_frame_for_data_entry.pack(fill=tk.X, pady=(10,0), padx=10) 

        add_data_button = ttk.Button(self.management_frame_for_data_entry, text="Add", command=self.open_data_entry_window)
        add_data_button.pack(side=tk.LEFT, padx=5, ipadx=10, ipady=3)
        change_data_button = ttk.Button(self.management_frame_for_data_entry, text="Change", command=self.open_modify_entry_window)
        change_data_button.pack(side=tk.LEFT, padx=5, ipadx=10, ipady=3)

        # Play controls frame
        play_controls_frame = ttk.Frame(self); play_controls_frame.pack(pady=10)
        self.play_button = ttk.Button(play_controls_frame, text="Play Selected", command=self.play_selected)
        self.play_button.pack(side="left", padx=(0, 20), ipadx=10, ipady=5)
        self.play_random_button = ttk.Button(play_controls_frame, text="Play Random", command=self.play_random_videos)
        self.play_random_button.pack(side="left", padx=(0, 5), ipadx=10, ipady=5)
        
        ttk.Label(play_controls_frame, text="Count:").pack(side="left", padx=(10,2))
        self.random_count_var.set("3")
        self.random_count_dropdown = ttk.Combobox(
            play_controls_frame, textvariable=self.random_count_var,
            values=["1", "2", "3", "5", "10", "All"], state="readonly",
            width=int(5*UI_SCALE), style="Custom.TCombobox"
        )
        self.random_count_dropdown.pack(side="left")
        
        self.change_score_checkbox = tk.Checkbutton(play_controls_frame, text="Change Score After Play", variable=self.change_score_var,
                                                    font=checkbox_font, bg=DARK_BG, fg=BRIGHT_FG, activebackground=DARK_BG, activeforeground=BRIGHT_FG, highlightthickness=0, bd=0, padx=8, pady=4,
                                                    image=self.checkbox_unchecked_img, selectimage=self.checkbox_checked_img, indicatoron=False, compound='left')
        self.change_score_checkbox.pack(side="left", padx=(20, 0))

        # Status bar (packed last to ensure it's at the very bottom)
        status_font = scale_font(("Arial", 16, "bold")) 
        status = tk.Label(self, textvariable=self.status_var, relief="sunken", anchor="w", font=status_font, bg=ACCENT, fg=BRIGHT_FG, padx=int(8*UI_SCALE), pady=int(6*UI_SCALE))
        status.pack(fill="x", side="bottom")
        self.status_var.set("Ready.")

    def open_data_entry_window(self):
        if self.data_entry_window_instance and self.data_entry_window_instance.winfo_exists():
            self.data_entry_window_instance.lift()
            self.data_entry_window_instance.focus_set()
            messagebox.showinfo("Window Open", "The Data Entry window is already open.", parent=self)
        else:
            # Pass the db_operations module to the DataEntryWindow
            self.data_entry_window_instance = data_entry_ui.DataEntryWindow(
                self, 
                db_ops=db_operations # Pass the imported module
            )
    
    
    def open_modify_entry_window(self):
        """Launch the ModifyEntryWindow for a single selected record."""
        sel = self.listbox.curselection()
        if len(sel) != 1:
            messagebox.showwarning("Selection", "Please select exactly one record to modify.", parent=self)
            return
        idx = int(sel[0])
        record = self.filtered_performances_data[idx]
        # If a modify window is already open, bring it to front
        if hasattr(self, 'modify_window') and self.modify_window and self.modify_window.winfo_exists():
            self.modify_window.lift()
            self.modify_window.focus_set()
            return
        # Open modify window, refresh performances on save/delete
        self.modify_window = modify_entry_ui.ModifyEntryWindow(self, record, self.load_performances)

    def disable_play_buttons(self):
        if self.play_button: self.play_button.config(state=tk.DISABLED)
        if self.play_random_button: self.play_random_button.config(state=tk.DISABLED)

    def enable_play_buttons(self):
        if self.play_button: self.play_button.config(state=tk.NORMAL)
        if self.play_random_button: self.play_random_button.config(state=tk.NORMAL)

    def clear_search(self):
        self.search_var.set(""); self.artist_var.set(""); self.date_var.set(""); self.filter_4k_var.set(False)
        self.show_mv_var.set(True); self.show_perf_var.set(True); self.show_url_only_var.set(True); self.show_local_var.set(True); self.show_new_var.set(False)
        self.update_list(apply_current_sort=True)

    # New keyboard navigation handler for artist combobox
    def handle_artist_combo_keypress(self, event):
        if event.char and event.char.isalnum():
            typed = event.char.lower()
            values = self.artist_dropdown.cget("values")
            if not values:
                return
            current = self.artist_var.get()
            try:
                idx = values.index(current)
                start = (idx + 1) % len(values)
            except ValueError:
                start = 0
            # Search forward from next index, then wrap around
            for i in list(range(start, len(values))) + list(range(0, start)):
                if values[i].lower().startswith(typed):
                    self.artist_var.set(values[i])
                    self.update_list(apply_current_sort=True)
                    return

    def load_artists(self):
        self.artists_list = db_operations.get_all_artists()
        # Sort artist names alphabetically, ignoring case, then add blank at top
        sorted_names = sorted([artist['name'] for artist in self.artists_list], key=lambda n: n.lower())
        artist_names = [""] + sorted_names
        self.artist_dropdown["values"] = artist_names
        if artist_names:
            self.artist_var.set(artist_names[0])

    def load_performances(self):
        self.status_var.set("Loading performances and music videos from database..."); self.update_idletasks()
        perf_rows = db_operations.get_all_performances_raw()
        mv_rows = db_operations.get_all_music_videos_raw()

        self.all_performances_data = []
        # Process performances
        for row in perf_rows:
            perf_dict = {
                "performance_id": row[0], "db_title": row[1] or "", "performance_date": row[2] or "N/A",
                "show_type": row[3] or "", "resolution": row[4] or "",
                "file_path1": row[5], "file_path2": row[6], "file_url": row[7], "score": row[8],
                "artists_str": row[9] or "N/A", "songs_str": row[10] or "N/A",
                "entry_type": "performance"
            }
            path, is_yt = utils.get_playable_path_info(perf_dict)
            perf_dict["playable_path"] = path; perf_dict["is_youtube"] = is_yt
            self.all_performances_data.append(perf_dict)
        # Process music videos
        for row in mv_rows:
            mv_dict = {
                "performance_id": f"mv_{row[0]}",  # Unique ID for MVs
                "db_title": row[1] or "", "performance_date": row[2] or "N/A",
                # Use file_path1 and file_path2 from the music_videos table
                "file_path1": row[4] if len(row) > 4 else None,  # file_path1
                "file_path2": row[5] if len(row) > 5 else None,  # file_path2
                "file_url": row[3],
                "score": row[6] if len(row) > 6 else None,
                "show_type": "", "resolution": "",
                "artists_str": row[7] if len(row) > 7 else (row[5] if len(row) > 5 else "N/A"),
                "songs_str": row[8] if len(row) > 8 else (row[6] if len(row) > 6 else "N/A"),
                "entry_type": "mv"
            }
            # Fallback for legacy tuple length (if needed)
            if mv_dict["file_path1"] is None and len(row) > 4 and isinstance(row[4], str):
                mv_dict["file_path1"] = row[4]
            if mv_dict["file_path2"] is None and len(row) > 5 and isinstance(row[5], str):
                mv_dict["file_path2"] = row[5]
            path, is_yt = utils.get_playable_path_info(mv_dict)
            mv_dict["playable_path"] = path; mv_dict["is_youtube"] = is_yt
            self.all_performances_data.append(mv_dict)
        self.update_list(apply_current_sort=True)
        self.pre_wake_external_drives()

    def sort_list_by(self, column_key):
        """Sort the performance list by the specified column"""
        # If clicking the same column, toggle sort order
        if self.sort_column == column_key:
            self.sort_ascending = not self.sort_ascending
        else:
            # New column, reset to ascending
            self.sort_column = column_key
            self.sort_ascending = True
            
        # Update headers to show sort indicator
        self._update_sort_indicators()
        
        # Refresh the list with sorting applied
        self.update_list(apply_current_sort=True)
            
    def update_list(self, apply_current_sort=False):
        artist_filter = self.artist_var.get().lower()
        date_filter = self.date_var.get()
        search_term = self.search_var.get().lower()
        filter_4k = self.filter_4k_var.get()
        show_mv = self.show_mv_var.get()
        show_perf = self.show_perf_var.get()
        show_url = self.show_url_only_var.get()
        show_local = self.show_local_var.get()
        show_new = self.show_new_var.get()
        self.filtered_performances_data = []
        self.listbox.delete(0, tk.END)
        for perf_data in self.all_performances_data:
            entry_type = perf_data.get("entry_type", "performance")
            # Filter by MV vs Performance
            if not ((show_mv and entry_type == "mv") or (show_perf and entry_type == "performance")):
                continue
            # Filter by source: URL vs Local file
            is_url_item = bool(perf_data.get("file_url"))
            if not ((show_url and is_url_item) or (show_local and not is_url_item)):
                continue
            if artist_filter and artist_filter not in perf_data.get("artists_str", "").lower(): continue
            if date_filter and not perf_data.get("performance_date", "").startswith(date_filter): continue
            if filter_4k:
                res_lower = perf_data.get("resolution", "").lower()
                if not any(keyword in res_lower for keyword in self.RESOLUTION_HIGH_QUALITY_KEYWORDS): continue
            # Filter new records (score 0 or None)
            if show_new:
                score_val = perf_data.get("score")
                if score_val is not None and score_val != 0: continue
            if not show_local and perf_data.get("file_url") is None:
                continue  # Skip items without a URL if show_url_only is checked

            if search_term:
                searchable_content = " ".join(filter(None, [
                    perf_data.get("performance_date"), perf_data.get("artists_str"),
                    perf_data.get("db_title"), perf_data.get("show_type"),
                    perf_data.get("resolution"), str(perf_data.get("score", "")),
                    perf_data.get("playable_path")
                ])).lower()
                if search_term not in searchable_content: continue
            
            self.filtered_performances_data.append(perf_data)
        
        # Apply sorting if needed
        if apply_current_sort and self.sort_column:
            self.apply_sorting()
        
        # Populate the listbox with possibly sorted data
        for perf_data in self.filtered_performances_data:
            # Format the display string
            disp_date = perf_data.get("performance_date", "N/A")[:12]
            disp_artists = perf_data.get("artists_str", "N/A")
            disp_perf_title = perf_data.get("db_title", "N/A") 
            # For MVs, leave show_type and resolution blank
            if perf_data.get("entry_type") == "mv":
                disp_show_type = ""
                disp_res = ""
            else:
                disp_show_type = perf_data.get("show_type", "N/A")
                disp_res = perf_data.get("resolution", "N/A")[:8]
            disp_score = str(perf_data.get("score")) if perf_data.get("score") is not None else ""
            
            source_text = "N/A"
            if perf_data.get("playable_path"):
                if perf_data.get("is_youtube"): source_text = "YouTube"
                elif perf_data.get("file_url"): source_text = "Web URL"
                else: source_text = "Local File"
            
            display_string = (f"{disp_date:<12} | {disp_artists:<30.30} | {disp_perf_title:<85.85} | "
                            f"{disp_show_type:<20.20} | {disp_res:<8.8} | {disp_score:<5} | {source_text}")
            
            self.listbox.insert(tk.END, display_string)
            
        self.status_var.set(f"{len(self.filtered_performances_data)} records match your filters.")

    def play_selected(self):
        if self.play_button and self.play_button.cget('state') == tk.DISABLED:
            self.status_var.set("Playback operation already in progress..."); self.update_idletasks(); return
        
        selected_indices = self.listbox.curselection()
        if not selected_indices: 
            messagebox.showinfo("No selection", "Please select one or more performances to play.", parent=self); return
        
        local_files_to_play, youtube_urls_to_open = [], []
        all_perf_details_for_callbacks, skipped_items_info = [], []

        for index_str in selected_indices:
            try:
                perf_idx = int(index_str)
                if 0 <= perf_idx < len(self.filtered_performances_data):
                    perf_dict = self.filtered_performances_data[perf_idx] 
                    path_or_url = perf_dict.get("playable_path")
                    is_yt = perf_dict.get("is_youtube", False)

                    if not path_or_url:
                        name_info = f"{perf_dict.get('artists_str','N/A')} ({perf_dict.get('db_title','N/A')})"
                        skipped_items_info.append(f"No path/URL for: {name_info}"); continue
                    
                    if is_yt:
                        youtube_urls_to_open.append(path_or_url)
                    elif perf_dict.get("file_url"): 
                        skipped_items_info.append(f"Non-YouTube URL playback not directly supported: {path_or_url[:60]}...")
                        continue 
                    else: 
                        local_files_to_play.append(path_or_url)
                    
                    if is_yt or (not perf_dict.get("file_url") and path_or_url): 
                        all_perf_details_for_callbacks.append(perf_dict)
            except ValueError: print(f"Warning: Could not parse selection index: {index_str}")
        
        if skipped_items_info: 
            messagebox.showwarning("Playback Warning", "Some items were skipped:\n- " + "\n- ".join(skipped_items_info), parent=self)
        
        if not local_files_to_play and not youtube_urls_to_open:
            self.status_var.set("Ready. No valid items to play from selection.")
            if not skipped_items_info:
                 messagebox.showinfo("No Playable Items", "No valid local files or YouTube URLs selected for playback.", parent=self)
            return
        
        self.disable_play_buttons()
        
        status_parts = []
        if local_files_to_play: status_parts.append(f"{len(local_files_to_play)} local file(s)")
        if youtube_urls_to_open: status_parts.append(f"{len(youtube_urls_to_open)} YouTube URL(s)")
        status_msg = f"Preparing {' and '.join(status_parts)}." if status_parts else "Preparing playback..."
        self.status_var.set(status_msg); self.update_idletasks()

        threading.Thread(
            target=KpopDBBrowser._execute_playback_sequence_and_callbacks, 
            args=(local_files_to_play, youtube_urls_to_open, all_perf_details_for_callbacks, self, False),
            daemon=True
        ).start()

    def play_random_videos(self):
        if self.play_random_button and self.play_random_button.cget('state') == tk.DISABLED:
            self.status_var.set("Playback operation already in progress..."); self.update_idletasks(); return
        if not self.filtered_performances_data: 
            messagebox.showinfo("No Videos", "No videos match current filters to play randomly.", parent=self); return
        
        try:
            count_str = self.random_count_var.get()
            num_to_sample = len(self.filtered_performances_data) if count_str.lower() == "all" else int(count_str)
        except ValueError: messagebox.showerror("Invalid Count", "Please select a valid number of videos.", parent=self); return
        if num_to_sample <= 0: messagebox.showinfo("Invalid Count", "Number of videos must be > 0.", parent=self); return

        actual_num_to_sample = min(num_to_sample, len(self.filtered_performances_data))
        chosen_perf_dicts = random.sample(self.filtered_performances_data, k=actual_num_to_sample)
        
        local_files_to_play, youtube_urls_to_open = [], []
        all_perf_details_for_callbacks = []

        for perf_dict in chosen_perf_dicts:
            path_or_url = perf_dict.get("playable_path")
            is_yt = perf_dict.get("is_youtube", False)
            if not path_or_url: continue

            if is_yt:
                youtube_urls_to_open.append(path_or_url)
                all_perf_details_for_callbacks.append(perf_dict)
            elif not perf_dict.get("file_url"): 
                local_files_to_play.append(path_or_url)
                all_perf_details_for_callbacks.append(perf_dict)
        
        if not local_files_to_play and not youtube_urls_to_open:
            messagebox.showinfo("No Playable Items", "No valid local video files or YouTube URLs found among random selection.", parent=self)
            self.status_var.set("Ready. No valid random items to play."); return
        
        self.disable_play_buttons()
        self.status_var.set(f"Preparing {len(all_perf_details_for_callbacks)} random item(s)..."); self.update_idletasks()

        threading.Thread(
            target=KpopDBBrowser._execute_playback_sequence_and_callbacks, 
            args=(local_files_to_play, youtube_urls_to_open, all_perf_details_for_callbacks, self, True),
            daemon=True
        ).start()

    @staticmethod
    def _execute_playback_sequence_and_callbacks(
        local_file_paths_list, youtube_url_list, all_processed_perf_details_dicts, 
        app_instance, is_random_source
    ):
        if not app_instance.winfo_exists(): return
        # Filter out non-string paths to avoid TypeError
        local_file_paths_list = [p for p in local_file_paths_list if isinstance(p, str)]
        if not local_file_paths_list and not youtube_url_list:
            app_instance.after(0, app_instance.enable_play_buttons)
            app_instance.after(0, lambda: app_instance.status_var.set("Ready. Nothing to play."))
            return

        mpv_played_count = 0
        if local_file_paths_list:
            first_local_file, num_local = local_file_paths_list[0], len(local_file_paths_list)
            first_basename = os.path.basename(first_local_file)
            mpv_proc = None
            try:
                msg = f"Accessing local: {first_basename} (1 of {num_local}). Waking drive..."
                if app_instance.winfo_exists(): app_instance.after(0, lambda: app_instance.status_var.set(msg))
                with open(first_local_file, "rb") as f: f.read(1)
                mpv_proc = subprocess.Popen([config.MPV_PLAYER_PATH, '--fs'] + local_file_paths_list)
                mpv_played_count = num_local
                if app_instance.winfo_exists():
                    status = f"Playing local: {first_basename}" if num_local == 1 else \
                             f"Playing {num_local} local files (starting with: {first_basename}). Waiting for player..."
                    app_instance.after(0, lambda: app_instance.status_var.set(status))
                mpv_proc.wait()
                if app_instance.winfo_exists(): app_instance.after(0, lambda: app_instance.status_var.set(f"Finished playing {num_local} local file(s)."))
            except FileNotFoundError:
                 if app_instance.winfo_exists():
                    err_msg = f"MPV player ('{config.MPV_PLAYER_PATH}') not found OR file access error for '{first_local_file}'."
                    app_instance.after(0, lambda: messagebox.showerror("Playback Error", err_msg, parent=app_instance))
                    app_instance.after(0, lambda: app_instance.status_var.set(f"Error: {err_msg}")); mpv_played_count = 0
            except Exception as e:
                if app_instance.winfo_exists():
                    err_msg = f"Could not play local files (starting with {first_local_file}): {e}"
                    app_instance.after(0, lambda: messagebox.showerror("Playback Error", err_msg, parent=app_instance))
                    app_instance.after(0, lambda: app_instance.status_var.set(f"Error playing local: {e}")); mpv_played_count = 0
            finally:
                if mpv_proc and mpv_proc.poll() is None:
                    try: mpv_proc.terminate()
                    except: pass
        
        yt_opened_count = 0
        if youtube_url_list:
            num_yt_urls = len(youtube_url_list)
            if app_instance.winfo_exists(): app_instance.after(0, lambda: app_instance.status_var.set(f"Opening {num_yt_urls} YouTube video(s)..."))
            for url in youtube_url_list:
                try:
                    p_url = urlparse(url); q_params = parse_qs(p_url.query)
                    q_params['autoplay'] = ['1']; q_params['rel'] = ['0'] 
                    final_url = urlunparse(list(p_url)[:4] + [urlencode(q_params, doseq=True)] + list(p_url)[5:])
                    if webbrowser.open_new_tab(final_url): yt_opened_count += 1
                except webbrowser.Error as e:
                    if app_instance.winfo_exists(): app_instance.after(0, lambda u=url, err=e: app_instance.status_var.set(f"Failed to open {u}: {err}"))
                except Exception as e: 
                    if app_instance.winfo_exists(): app_instance.after(0, lambda u=url, err=e: app_instance.status_var.set(f"Error processing URL {u}: {err}"))
            if app_instance.winfo_exists():
                status_parts = []
                if local_file_paths_list: status_parts.append(f"{mpv_played_count} local file(s) processed.")
                status_parts.append(f"{yt_opened_count} of {num_yt_urls} YouTube video(s) opened.")
                app_instance.after(0, lambda: app_instance.status_var.set(" ".join(status_parts) if status_parts else "No media actions taken."))

        if app_instance.winfo_exists():
            app_instance.after(100, app_instance.enable_play_buttons) 
            if all_processed_perf_details_dicts:
                total_items = len(all_processed_perf_details_dicts)
                summary = f"Playback actions complete for {total_items} item(s). "
                if app_instance.change_score_var.get(): summary += "Score editor opening..."
                elif is_random_source: summary += "Info window opening..."
                else: summary += "Ready."
                app_instance.after(500, lambda fs=summary: app_instance.status_var.set(fs))
                if app_instance.change_score_var.get():
                    app_instance.after(600, lambda: app_instance.open_score_editor(all_processed_perf_details_dicts, is_random_source))
                elif is_random_source: 
                    app_instance.after(600, lambda: app_instance.show_played_info_window(all_processed_perf_details_dicts))
            else: 
                app_instance.after(500, lambda: app_instance.status_var.set("Ready. No valid items were processed for further actions."))

    def show_played_info_window(self, played_details_dicts):
        if not played_details_dicts: return
        info_win = tk.Toplevel(self); info_win.title("Played Performance Details"); info_win.geometry(f"{int(800*UI_SCALE)}x{int(500*UI_SCALE)}") 
        info_win.configure(bg=DARK_BG); info_win.transient(self); info_win.grab_set()
        txt_frame = ttk.Frame(info_win); txt_frame.pack(fill=tk.BOTH, expand=True, padx=int(10*UI_SCALE), pady=(int(10*UI_SCALE),0))
        txt_area = tk.Text(txt_frame, wrap=tk.WORD, font=FONT_MAIN, bg=DARK_BG, fg=BRIGHT_FG, relief="flat", borderwidth=0,
                            selectbackground="#44475a", selectforeground="#f1fa8c", insertbackground=BRIGHT_FG)
        vscroll = ttk.Scrollbar(txt_frame, orient="vertical", command=txt_area.yview, style="Vertical.TScrollbar")
        txt_area.configure(yscrollcommand=vscroll.set); vscroll.pack(side="right", fill="y"); txt_area.pack(side="left", fill=tk.BOTH, expand=True)
        txt_area.insert(tk.END, f"Details of {len(played_details_dicts)} played performance(s):\n\n")
        
        for i, perf_dict in enumerate(played_details_dicts):
            artists = perf_dict.get("artists_str", "N/A")
            date = perf_dict.get("performance_date", "N/A")
            db_title = perf_dict.get("db_title", "N/A") 
            show = perf_dict.get("show_type", "N/A") 
            score = str(perf_dict.get("score")) if perf_dict.get("score") is not None else "N/A"
            
            path_info = perf_dict.get("playable_path", "N/A")
            if perf_dict.get("is_youtube"): path_info = f"YouTube: {path_info}"
            elif perf_dict.get("file_url"): path_info = f"URL: {path_info}"
            else: path_info = f"File: {path_info}"

            txt_area.insert(tk.END, f"{i+1}. Artist(s): {artists}\n")
            txt_area.insert(tk.END, f"   Date:  {date}\n")
            txt_area.insert(tk.END, f"   Title: {db_title}\n") 
            txt_area.insert(tk.END, f"   Show:  {show}\n")   
            txt_area.insert(tk.END, f"   Score: {score}\n")
            txt_area.insert(tk.END, f"   Source: {path_info}\n\n")
        txt_area.config(state=tk.DISABLED)
        ttk.Button(info_win, text="Close", command=info_win.destroy).pack(pady=int(10*UI_SCALE))
        info_win.focus_set()

    def open_score_editor(self, played_performance_details_dicts, is_random_source=False):
        if self.score_editor_window and self.score_editor_window.winfo_exists():
            self.score_editor_window.lift(); self.score_editor_window.focus_set()
            messagebox.showwarning("Editor Open", "The score editor window is already open.", parent=self); return
        if not played_performance_details_dicts: 
            messagebox.showinfo("No Details", "No performance details available to edit scores.", parent=self); return
        
        current_db_conn = db_operations.get_db_connection()
        if not current_db_conn:
            messagebox.showerror("Database Error", "Cannot open score editor: No database connection.", parent=self)
            return

        prefix = "Randomly Played" if is_random_source else "Selected"
        self.score_editor_window = ScoreEditorWindow(self, f"{prefix} Items - Score Editor", 
                                                     played_performance_details_dicts, 
                                                     current_db_conn, 
                                                     self.refresh_data_and_ui)

    def refresh_data_and_ui(self):
        if self.score_editor_window and not self.score_editor_window.winfo_exists():
             self.score_editor_window = None
        elif self.score_editor_window:
            self.score_editor_window.destroy_and_clear_master_ref()
        
        self.load_performances()
        self.status_var.set("Data refreshed. Scores may have been updated."); self.enable_play_buttons()

    def _set_header_hover(self, label, is_hovering):
        """Change header appearance on hover"""
        # Don't change appearance if this is the sorted column
        col_index = self.header_labels.index(label) if label in self.header_labels else -1
        if col_index >= 0 and self.column_info[col_index]["key"] == self.sort_column:
            return
            
        if is_hovering:
            label.config(bg="#334455")  # Slightly lighter background on hover
        else:
            label.config(bg=DARK_BG)    # Reset to default background
    
    def _update_sort_indicators(self):
        """Update all header labels to reflect current sort state"""
        if not hasattr(self, 'header_labels'):
            return
            
        for i, label in enumerate(self.header_labels):
            if i < len(self.column_info):
                col = self.column_info[i]
                is_sorted = (col["key"] == self.sort_column)
                
                if is_sorted:
                    # Add sort indicator to sorted column
                    indicator = "▲" if self.sort_ascending else "▼"
                    label.config(
                        text=f"{col['name']} {indicator:<{col['width'] - len(col['name']) - 1}}",
                        bg="#2a3344",  # Highlight background for sorted column
                        relief="raised"  # Give it a raised appearance
                    )
                else:
                    # Reset other columns
                    label.config(
                        text=f"{col['name']:<{col['width']}}",
                        bg=DARK_BG,
                        relief="flat"
                    )
    
    def apply_sorting(self):
        """Sort the filtered_performances_data based on current sort column and direction"""
        if not self.sort_column:
            return
        
        def get_sort_key(item):
            if self.sort_column == "score":
                # Score requires special handling as it might be None or numeric
                val = item.get(self.sort_column)
                if val is None:
                    return -1 if self.sort_ascending else float('inf')
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return -1 if self.sort_ascending else float('inf')
            elif self.sort_column == "source":
                # Source isn't directly in the data, need to derive it
                if item.get("is_youtube"):
                    return "YouTube"
                elif item.get("file_url"):
                    return "Web URL"
                elif item.get("playable_path"):
                    return "Local File"
                else:
                    return "N/A"
            else:
                # Default string-based comparison, with None/empty handling
                val = item.get(self.sort_column, "")
                if val is None:
                    val = ""
                return str(val).lower()  # Case-insensitive sorting
        
        # Apply the sort
        self.filtered_performances_data.sort(
            key=get_sort_key,
            reverse=not self.sort_ascending
        )
    
    def pre_wake_external_drives(self):
        if not self.all_performances_data: return
        
        local_paths_for_wake = []
        for perf_data in self.all_performances_data:
            playable_path = perf_data.get("playable_path")
            is_url = perf_data.get("file_url") and playable_path == perf_data.get("file_url")
            # Only add if playable_path is a string (not int/None)
            if playable_path and not is_url and isinstance(playable_path, str):
                local_paths_for_wake.append(playable_path)
        if not local_paths_for_wake: return

        unique_dirs = sorted(list(set(os.path.dirname(p) for p in local_paths_for_wake if isinstance(p, str) and os.path.dirname(p))))
        if not unique_dirs: return

        dirs_to_ping = []
        if unique_dirs:
            dirs_to_ping.append(unique_dirs[0])
            if len(unique_dirs) > 2: 
                mid_idx = len(unique_dirs) // 2
                if unique_dirs[mid_idx] != dirs_to_ping[0] and not unique_dirs[mid_idx].startswith(dirs_to_ping[0] + os.sep):
                    dirs_to_ping.append(unique_dirs[mid_idx])
            if len(unique_dirs) > 1: 
                last_dir = unique_dirs[-1]
                if not any(last_dir == ed or last_dir.startswith(ed + os.sep) for ed in dirs_to_ping):
                    dirs_to_ping.append(last_dir)
        
        dirs_to_ping = sorted(list(set(dirs_to_ping)))[:3]
        if not dirs_to_ping: return
            
        disp_dirs = ", ".join([os.path.basename(p) if os.path.basename(p) else p for p in dirs_to_ping])
        current_status = self.status_var.get()
        if not any(s in current_status for s in ["Loading", "Playing", "Accessing"]):
             self.status_var.set(f"Pre-waking drives (e.g., {disp_dirs})..."); self.update_idletasks()
        
        threading.Thread(target=KpopDBBrowser._execute_pre_wake, args=(dirs_to_ping, self), daemon=True).start()

    @staticmethod
    def _execute_pre_wake(dir_paths, app_instance): 
        if not app_instance.winfo_exists(): return
        woken, errors = 0, 0
        for d_path in dir_paths:
            try:
                if os.path.isdir(d_path): os.listdir(d_path); woken += 1
            except Exception: errors += 1
        
        if app_instance.winfo_exists():
            current_status = app_instance.status_var.get()
            if not any(s in current_status for s in ["Loading", "Playing", "Accessing"]):
                msg = f"Pre-wake: {woken} paths accessed."
                if errors > 0: msg += f" ({errors} issues)."
                else: msg += " Ready."
                app_instance.after(0, lambda: app_instance.status_var.set(msg))

    def update_artists_from_spotify(self):
        base_dir = os.path.dirname(__file__)
        album_importer = os.path.join(base_dir, "accesories/spotify_data/spotify_album_importer.py")
        artist_info_importer = os.path.join(base_dir, "accesories/spotify_data/spotify_artist_info_importer.py")
        try:
            subprocess.run([sys.executable, album_importer], check=True)
            subprocess.run([sys.executable, artist_info_importer], check=True)
            self.load_initial_data()
            messagebox.showinfo("Artists Updated", "Artists have been updated and enriched from Spotify.", parent=self)
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"Failed to update artists from Spotify.\n\nScript exited with code {e.returncode}. See terminal for details.", parent=self)
        except Exception as e:
            messagebox.showerror("Error", f"Unexpected error: {e}", parent=self)

    def open_data_entry_window(self):
        if self.data_entry_window_instance and self.data_entry_window_instance.winfo_exists():
            self.data_entry_window_instance.lift()
            self.data_entry_window_instance.focus_set()
            messagebox.showinfo("Window Open", "The Data Entry window is already open.", parent=self)
        else:
            # Pass the db_operations module to the DataEntryWindow
            self.data_entry_window_instance = data_entry_ui.DataEntryWindow(
                self, 
                db_ops=db_operations # Pass the imported module
            )
    
    
    def on_closing(self): 
        if self.score_editor_window and self.score_editor_window.winfo_exists():
            self.score_editor_window.cancel() 
            if self.score_editor_window and self.score_editor_window.winfo_exists():
                self.score_editor_window.destroy_and_clear_master_ref()
                self.score_editor_window = None 
        
        if self.data_entry_window_instance and self.data_entry_window_instance.winfo_exists():
            self.data_entry_window_instance.close_window()
            self.data_entry_window_instance = None

        db_operations.close_db_connection()
        
        try:
            super().destroy() 
        except tk.TclError as e:
            print(f"TclError during main window destroy: {e}. (Often benign on final exit)")
        except Exception as e:
            print(f"Other error during main window destroy: {e}")

if __name__ == "__main__":

    
    try:
        app = KpopDBBrowser() 
        app.protocol("WM_DELETE_WINDOW", app.on_closing)
        app.mainloop()
    except Exception as e:
        print(f"CRITICAL ERROR in __main__ GUI phase: {e}")
        import traceback
        traceback.print_exc()
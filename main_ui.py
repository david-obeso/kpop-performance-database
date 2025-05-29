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

# Constants
DARK_BG = "#222222"
BRIGHT_FG = "#f8f8f2"
ACCENT = "#44475a"
FONT_MAIN = ("Courier New", 13)
FONT_HEADER = ("Courier New", 13, "bold")
FONT_LABEL_SMALL = ("Courier New", 11)
FONT_STATUS = ("Arial", 13)
FONT_BUTTON = ("Arial", 13, "bold")

APP_VERSION = "4.0.2 (Data Entry UI - Phase 1)" # Updated version

class ScoreEditorWindow(tk.Toplevel): # Keep this class definition as it was
    def __init__(self, master, title, performance_details_list_dicts, db_connection, refresh_callback):
        super().__init__(master)
        self.title(title)
        self.geometry("950x720") 
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
        self.geometry("2200x950") 
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
        
        self.RESOLUTION_HIGH_QUALITY_KEYWORDS = ["4k", "upscaled", "ai"]
        self.status_var = tk.StringVar(value="Initializing...")
        self.play_button = None; self.play_random_button = None
        self.random_count_var = tk.StringVar(); self.random_count_dropdown = None
        self.change_score_var = tk.BooleanVar(value=False)
        self.score_editor_window = None
        self.data_entry_window_instance = None # For the new data entry window

        self.create_widgets()
        self.load_artists() 
        self.load_performances()

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
        style.configure("Custom.TCombobox", font=("Courier New", 16, "bold"), selectbackground=ACCENT, selectforeground=BRIGHT_FG)
        style.map("Custom.TCombobox",
            fieldbackground=[('readonly', '#333a40'), ('disabled', '#2a2a2a')],
            foreground=[('readonly', BRIGHT_FG), ('disabled', '#777777')],
            background=[('readonly', ACCENT), ('active', '#6272a4'), ('disabled', '#303030')],
            arrowcolor=[('readonly', BRIGHT_FG),('active', BRIGHT_FG),('disabled', '#777777')]
        )
        style.configure("TCheckbutton", background=DARK_BG, foreground=BRIGHT_FG, font=FONT_MAIN)
        style.map("TCheckbutton", indicatorcolor=[('selected', ACCENT), ('!selected', '#555555')], background=[('active', DARK_BG)])
        style.configure("Vertical.TScrollbar", troughcolor=DARK_BG, background=ACCENT, arrowcolor=BRIGHT_FG)
        style.map("Vertical.TScrollbar", background=[("active", "#6272a4")])
        style.configure("Horizontal.TScrollbar", troughcolor=DARK_BG, background=ACCENT, arrowcolor=BRIGHT_FG)
        style.map("Horizontal.TScrollbar", background=[("active", "#6272a4")])

        filter_frame = ttk.Frame(self); filter_frame.pack(fill="x", padx=10, pady=8)
        ttk.Label(filter_frame, text="Artist:").pack(side="left")
        self.artist_var = tk.StringVar()
        self.artist_dropdown = ttk.Combobox(filter_frame, textvariable=self.artist_var, state="readonly", style="Custom.TCombobox", width=25)
        self.artist_dropdown.pack(side="left", padx=5, ipadx=5, ipady=6)
        self.artist_dropdown.bind("<<ComboboxSelected>>", lambda e: self.update_list())
        
        ttk.Label(filter_frame, text="Date (YYYY or YYYY-MM):").pack(side="left", padx=(15,0))
        self.date_var = tk.StringVar()
        date_entry = tk.Entry(filter_frame, textvariable=self.date_var, width=10, font=FONT_MAIN, bg=DARK_BG, fg=BRIGHT_FG, insertbackground=BRIGHT_FG)
        date_entry.pack(side="left", padx=5, ipadx=5, ipady=3); date_entry.bind("<KeyRelease>", lambda e: self.update_list())
        
        ttk.Label(filter_frame, text="4K?:").pack(side="left", padx=(15,0))
        self.filter_4k_var = tk.BooleanVar(value=False)
        filter_4k_checkbutton = ttk.Checkbutton(filter_frame, variable=self.filter_4k_var, command=self.update_list)
        filter_4k_checkbutton.pack(side="left", padx=(2, 10))
        
        ttk.Label(filter_frame, text="Search:").pack(side="left", padx=(10,0))
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(filter_frame, textvariable=self.search_var, font=FONT_MAIN, bg=DARK_BG, fg=BRIGHT_FG, insertbackground=BRIGHT_FG)
        search_entry.pack(side="left", fill="x", expand=True, padx=5, ipadx=5, ipady=3); search_entry.bind("<KeyRelease>", lambda e: self.update_list())
        
        ttk.Button(filter_frame, text="Clear", command=self.clear_search).pack(side="left", padx=5, ipadx=8, ipady=3)

        header_text = (f"{'Date':<12} | {'Artist(s)':<30} | {'Performance Title':<50} | {'Show Type':<25} | "
                       f"{'Res':<8} | {'Score':<5} | {'Source'}")
        header = tk.Label(self, text=header_text, font=FONT_HEADER, anchor="w", bg=DARK_BG, fg=BRIGHT_FG)
        header.pack(fill="x", padx=10, pady=(5,0))

        listbox_frame = tk.Frame(self, bg=DARK_BG); listbox_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.listbox = tk.Listbox(listbox_frame, font=FONT_MAIN, bg=DARK_BG, fg=BRIGHT_FG,
            selectbackground="#44475a", selectforeground="#f1fa8c", highlightbackground=ACCENT, highlightcolor=ACCENT,
            activestyle="none", relief="flat", borderwidth=0, selectmode=tk.EXTENDED)
        
        vscroll = ttk.Scrollbar(listbox_frame, orient="vertical", style="Vertical.TScrollbar", command=self.listbox.yview) 
        hscroll = ttk.Scrollbar(listbox_frame, orient="horizontal", style="Horizontal.TScrollbar", command=self.listbox.xview)

        self.listbox.configure(yscrollcommand=vscroll.set, xscrollcommand=hscroll.set)

        vscroll.pack(side="right", fill="y")
        hscroll.pack(side="bottom", fill="x")
        self.listbox.pack(side="left", fill="both", expand=True)
        
        self.listbox.bind("<Double-Button-1>", lambda e: self.play_selected())

        # Management frame for Add/Modify Data button
        self.management_frame_for_data_entry = ttk.Frame(self)
        self.management_frame_for_data_entry.pack(fill=tk.X, pady=(10,0), padx=10) 

        add_data_button = ttk.Button(self.management_frame_for_data_entry, text="Add/Modify Data", command=self.open_data_entry_window)
        add_data_button.pack(side=tk.LEFT, padx=5, ipadx=10, ipady=3)

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
            width=5, style="Custom.TCombobox"
        )
        self.random_count_dropdown.pack(side="left")
        
        self.change_score_checkbox = ttk.Checkbutton(play_controls_frame, text="Change Score After Play", variable=self.change_score_var)
        self.change_score_checkbox.pack(side="left", padx=(20, 0))

        # Status bar (packed last to ensure it's at the very bottom)
        status_font = ("Arial", 16, "bold") 
        status = tk.Label(self, textvariable=self.status_var, relief="sunken", anchor="w", font=status_font, bg=ACCENT, fg=BRIGHT_FG, padx=8, pady=6)
        status.pack(fill="x", side="bottom")
        self.status_var.set("Ready.")


    def open_data_entry_window(self):
        if self.data_entry_window_instance and self.data_entry_window_instance.winfo_exists():
            self.data_entry_window_instance.lift()
            self.data_entry_window_instance.focus_set()
            messagebox.showinfo("Window Open", "The Data Entry window is already open.", parent=self)
        else:
            self.data_entry_window_instance = data_entry_ui.DataEntryWindow(self)

    def disable_play_buttons(self):
        if self.play_button: self.play_button.config(state=tk.DISABLED)
        if self.play_random_button: self.play_random_button.config(state=tk.DISABLED)

    def enable_play_buttons(self):
        if self.play_button: self.play_button.config(state=tk.NORMAL)
        if self.play_random_button: self.play_random_button.config(state=tk.NORMAL)

    def clear_search(self):
        self.search_var.set(""); self.artist_var.set(""); self.date_var.set(""); self.filter_4k_var.set(False)
        self.update_list()

    def load_artists(self):
        self.artists_list = db_operations.get_all_artists() 
        artist_names = [""] + [artist['name'] for artist in self.artists_list]
        self.artist_dropdown["values"] = artist_names
        if artist_names: 
            self.artist_var.set(artist_names[0])

    def load_performances(self):
        self.status_var.set("Loading performances from database..."); self.update_idletasks()
        raw_rows = db_operations.get_all_performances_raw()
        
        self.all_performances_data = []
        for row in raw_rows: 
            perf_dict = {
                "performance_id": row[0], "db_title": row[1] or "", "performance_date": row[2] or "N/A",
                "show_type": row[3] or "N/A", "resolution": row[4] or "N/A",
                "file_path1": row[5], "file_path2": row[6], "file_url": row[7], "score": row[8],
                "artists_str": row[9] or "N/A", "songs_str": row[10] or "N/A" 
            }
            path, is_yt = utils.get_playable_path_info(perf_dict) 
            perf_dict["playable_path"] = path; perf_dict["is_youtube"] = is_yt
            self.all_performances_data.append(perf_dict)
            
        self.update_list()
        self.pre_wake_external_drives()

    def update_list(self):
        artist_filter = self.artist_var.get().lower()
        date_filter = self.date_var.get()
        search_term = self.search_var.get().lower()
        filter_4k = self.filter_4k_var.get()

        self.filtered_performances_data = []
        self.listbox.delete(0, tk.END)

        for perf_data in self.all_performances_data:
            if artist_filter and artist_filter not in perf_data.get("artists_str", "").lower(): continue
            if date_filter and not perf_data.get("performance_date", "").startswith(date_filter): continue
            if filter_4k:
                res_lower = perf_data.get("resolution", "").lower()
                if not any(keyword in res_lower for keyword in self.RESOLUTION_HIGH_QUALITY_KEYWORDS): continue
            
            disp_date = perf_data.get("performance_date", "N/A")[:12]
            disp_artists = perf_data.get("artists_str", "N/A")
            disp_perf_title = perf_data.get("db_title", "N/A") 
            disp_show_type = perf_data.get("show_type", "N/A")
            disp_res = perf_data.get("resolution", "N/A")[:8]
            disp_score = str(perf_data.get("score")) if perf_data.get("score") is not None else ""
            
            source_text = "N/A"
            if perf_data.get("playable_path"):
                if perf_data.get("is_youtube"): source_text = "YouTube"
                elif perf_data.get("file_url"): source_text = "Web URL"
                else: source_text = "Local File"
            
            display_string = (f"{disp_date:<12} | {disp_artists:<30.30} | {disp_perf_title:<50.50} | "
                              f"{disp_show_type:<25.25} | {disp_res:<8.8} | {disp_score:<5} | {source_text}")

            if search_term:
                searchable_content = " ".join(filter(None, [
                    perf_data.get("performance_date"), perf_data.get("artists_str"),
                    perf_data.get("db_title"), perf_data.get("show_type"),
                    perf_data.get("resolution"), str(perf_data.get("score", "")),
                    perf_data.get("playable_path")
                ])).lower()
                if search_term not in searchable_content: continue
            
            self.filtered_performances_data.append(perf_data)
            self.listbox.insert(tk.END, display_string)
            
        self.status_var.set(f"{len(self.filtered_performances_data)} performances match your filters.")

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
                mpv_proc = subprocess.Popen([config.MPV_PLAYER_PATH] + local_file_paths_list)
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
        info_win = tk.Toplevel(self); info_win.title("Played Performance Details"); info_win.geometry("800x500") 
        info_win.configure(bg=DARK_BG); info_win.transient(self); info_win.grab_set()
        txt_frame = ttk.Frame(info_win); txt_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10,0))
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
        ttk.Button(info_win, text="Close", command=info_win.destroy).pack(pady=10)
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

    def pre_wake_external_drives(self):
        if not self.all_performances_data: return
        
        local_paths_for_wake = []
        for perf_data in self.all_performances_data:
            playable_path = perf_data.get("playable_path")
            is_url = perf_data.get("file_url") and playable_path == perf_data.get("file_url")
            if playable_path and not is_url: 
                 local_paths_for_wake.append(playable_path)
        
        if not local_paths_for_wake: return

        unique_dirs = sorted(list(set(os.path.dirname(p) for p in local_paths_for_wake if p and os.path.dirname(p))))
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
        mount_script_path = "/home/david/mount_windows_shares.sh" # Verify this path
        if os.path.exists(mount_script_path):
            process = subprocess.run(
                [mount_script_path],
                check=False, capture_output=True, text=True, timeout=15 
            )
            if process.returncode != 0:
                error_message = f"Could not mount Windows shares!\nScript: {mount_script_path}\nOutput:\n{process.stdout}\n{process.stderr}\n\nThe program will now exit."
                show_startup_error_and_exit("Mount Error", error_message)
            print("Windows shares mounted (or already mounted).")
        else:
            error_message = f"Mount script '{mount_script_path}' not found.\nThe program will now exit."
            show_startup_error_and_exit("Mount Error", error_message)

    except FileNotFoundError:
        error_message = f"Mount script '{mount_script_path}' not found (FileNotFoundError for subprocess).\nThe program will now exit."
        show_startup_error_and_exit("Mount Error", error_message)
    except subprocess.TimeoutExpired:
        error_message = "Mount script timed out after 15 seconds.\nThe program will now exit."
        show_startup_error_and_exit("Mount Error", error_message)
    except Exception as e: 
        error_message = f"An unexpected error occurred during mounting: {e}\nThe program will now exit."
        show_startup_error_and_exit("Mount Error", error_message)
    
    try:
        app = KpopDBBrowser() 
        app.protocol("WM_DELETE_WINDOW", app.on_closing)
        app.mainloop()
    except Exception as e:
        print(f"CRITICAL ERROR in __main__ GUI phase: {e}")
        import traceback
        traceback.print_exc()
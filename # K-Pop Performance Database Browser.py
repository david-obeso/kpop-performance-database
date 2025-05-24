# K-Pop Performance Database Browser
# Version 3.3.0 (YouTube URL Playback & Unified Playback Handling)
import os
import subprocess
import sqlite3
import sys
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import random
import webbrowser # Added for opening URLs
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode # Added for URL manipulation

DATABASE_FILE = "kpop_database.db"
MPV_PLAYER_PATH = "mpv"

DARK_BG = "#222222"
BRIGHT_FG = "#f8f8f2"
ACCENT = "#44475a"
FONT_MAIN = ("Courier New", 13)
FONT_HEADER = ("Courier New", 13, "bold") # Used for the score number
FONT_LABEL_SMALL = ("Courier New", 11) # For "Score Change" label
FONT_STATUS = ("Arial", 13) # Note: Status bar in main app uses Arial 16 bold
FONT_BUTTON = ("Arial", 13, "bold")

class ScoreEditorWindow(tk.Toplevel):
    def __init__(self, master, title, performance_details_list, db_connection, refresh_callback):
        super().__init__(master)
        self.title(title)
        self.geometry("950x650")
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

        header_label = ttk.Label(main_frame, text=f"Editing scores for {len(performance_details_list)} item(s): (0-5 points)",
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

        for perf_details in performance_details_list:
            perf_id = perf_details[0]
            group = perf_details[1] or "N/A"
            date = perf_details[2] or "N/A"
            show = perf_details[3] or "N/A"
            original_score = perf_details[6] if perf_details[6] is not None else 0
            songs_text_full = perf_details[7] or ""
            songs_text_display = songs_text_full[:80] + ('...' if len(songs_text_full) > 80 else '')

            item_frame = ttk.Frame(self.scrollable_frame, style="TFrame", padding=(5,0,5,5))
            item_frame.pack(fill="x", pady=(0, 10), padx=2)

            text_info_frame = ttk.Frame(item_frame, style="TFrame")
            text_info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 15))
            text_info_frame.columnconfigure(0, weight=0, minsize=60)
            text_info_frame.columnconfigure(1, weight=1)
            row_idx = 0
            for label_text, value_text, wrap_len in [
                ("Group:", group, 400), ("Date:", date, 0), ("Show:", show, 400), ("Songs:", songs_text_display, 450)
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
            score_label.config(text=str(score_var.get())) # Ensure initial text is set


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
        # Update text immediately for the specific label
        for item_data in self.performance_items_data:
            if item_data["score_var"] == score_var:
                item_data["score_label_widget"].config(text=str(score_var.get())) # Update text
                break
        self.update_button_states(score_var.get(), plus_btn, minus_btn)


    def update_button_states(self, score, plus_btn, minus_btn):
        plus_btn.config(state=tk.NORMAL if score < 5 else tk.DISABLED)
        minus_btn.config(state=tk.NORMAL if score > 0 else tk.DISABLED)

    def save_changes(self):
        updates_made = 0
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
            # self.destroy_and_clear_master_ref() # Moved to refresh_callback or cancel

    def cancel(self):
        if any(item["score_var"].get() != item["original_score"] for item in self.performance_items_data):
            if not messagebox.askyesno("Confirm Cancel", "Unsaved changes. Are you sure you want to cancel?", parent=self):
                return
        self.destroy_and_clear_master_ref()

    def destroy_and_clear_master_ref(self):
        if hasattr(self.master, 'score_editor_window') and self.master.score_editor_window == self:
            self.master.score_editor_window = None
        self.destroy()

class KpopDBBrowser(tk.Tk):
    def __init__(self):
        print("Attempting to mount Windows shares. Please enter your password in the console if prompted...")
        try:
            process = subprocess.run(
                ["/home/david/mount_windows_shares.sh"], # User specific script
                check=False, capture_output=True, text=True, timeout=15 
            )
            if process.returncode != 0:
                error_message = f"Could not mount Windows shares!\n\nScript output:\n{process.stdout}\n{process.stderr}\n\nThe program will now exit."
                print(error_message); root_temp = tk.Tk(); root_temp.withdraw(); messagebox.showerror("Mount Error", error_message, parent=None); root_temp.destroy(); sys.exit(1)
            print("Windows shares mounted (or already mounted).")
        except FileNotFoundError:
            error_message = "Mount script '/home/david/mount_windows_shares.sh' not found.\nThe program will now exit."
            print(error_message); root_temp = tk.Tk(); root_temp.withdraw(); messagebox.showerror("Mount Error", error_message, parent=None); root_temp.destroy(); sys.exit(1)
        except subprocess.TimeoutExpired:
            error_message = "Mount script timed out after 15 seconds.\nThe program will now exit."
            print(error_message); root_temp = tk.Tk(); root_temp.withdraw(); messagebox.showerror("Mount Error", error_message, parent=None); root_temp.destroy(); sys.exit(1)
        except Exception as e:
            error_message = f"An unexpected error occurred during mounting: {e}\nThe program will now exit."
            print(error_message); root_temp = tk.Tk(); root_temp.withdraw(); messagebox.showerror("Mount Error", error_message, parent=None); root_temp.destroy(); sys.exit(1)

        super().__init__()
        self.title("K-Pop Performance Database Browser v3.3.0") 
        self.geometry("2100x900")
        self.configure(bg=DARK_BG)

        # Colors for Combobox Listbox (dropdown part)
        combobox_list_bg = '#333a40' 
        combobox_list_select_bg = ACCENT
        combobox_list_select_fg = '#f1fa8c'
        self.option_add('*TCombobox*Listbox.background', combobox_list_bg)
        self.option_add('*TCombobox*Listbox.foreground', BRIGHT_FG)
        self.option_add('*TCombobox*Listbox.selectBackground', combobox_list_select_bg)
        self.option_add('*TCombobox*Listbox.selectForeground', combobox_list_select_fg)
        self.option_add('*TCombobox*Listbox.font', FONT_MAIN) 
        self.option_add('*TCombobox*Listbox.relief', 'flat')
        self.option_add('*TCombobox*Listbox.borderwidth', 0)

        self.conn = sqlite3.connect(DATABASE_FILE)
        self.performances = []
        self.filtered = []
        self.groups = []
        self.RESOLUTION_HIGH_QUALITY_KEYWORDS = ["4k", "upscaled", "ai"]
        self.status_var = tk.StringVar(value="Initializing...")
        self.play_button = None; self.play_random_button = None
        self.random_count_var = tk.StringVar(); self.random_count_dropdown = None
        # self.currently_playing_random_details = [] # No longer needed directly here
        self.change_score_var = tk.BooleanVar(value=False)
        self.score_editor_window = None

        self.create_widgets()
        self.load_groups()
        self.load_performances() # This will also trigger pre_wake_external_drives
        # self.pre_wake_external_drives() # Called at the end of load_performances

    @staticmethod
    def is_youtube_url(path_string):
        if not path_string:
            return False
        path_string_lower = path_string.lower()
        return path_string_lower.startswith("https://www.youtube.com/") or \
               path_string_lower.startswith("https://youtu.be/") or \
               path_string_lower.startswith("http://www.youtube.com/") or \
               path_string_lower.startswith("http://youtu.be/")

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

        style.configure("Custom.TCombobox",
            font=("Courier New", 16, "bold"), 
            selectbackground=ACCENT,          
            selectforeground=BRIGHT_FG        
        )
        style.map("Custom.TCombobox",
            fieldbackground=[
                ('readonly', '#333a40'),  
                ('disabled', '#2a2a2a')  
            ],
            foreground=[
                ('readonly', BRIGHT_FG),   
                ('disabled', '#777777')    
            ],
            background=[ 
                ('readonly', ACCENT),      
                ('active', '#6272a4'),     
                ('disabled', '#303030')    
            ],
            arrowcolor=[ 
                ('readonly', BRIGHT_FG),
                ('active', BRIGHT_FG),     
                ('disabled', '#777777')    
            ]
        )
        
        style.configure("TCheckbutton", background=DARK_BG, foreground=BRIGHT_FG, font=FONT_MAIN)
        style.map("TCheckbutton", indicatorcolor=[('selected', ACCENT), ('!selected', '#555555')], background=[('active', DARK_BG)])
        style.configure("Vertical.TScrollbar", troughcolor=DARK_BG, background=ACCENT, arrowcolor=BRIGHT_FG)
        style.map("Vertical.TScrollbar", background=[("active", "#6272a4")])
        style.configure("Horizontal.TScrollbar", troughcolor=DARK_BG, background=ACCENT, arrowcolor=BRIGHT_FG)
        style.map("Horizontal.TScrollbar", background=[("active", "#6272a4")])

        filter_frame = ttk.Frame(self); filter_frame.pack(fill="x", padx=10, pady=8)
        ttk.Label(filter_frame, text="Group:").pack(side="left")
        self.group_var = tk.StringVar()
        self.group_dropdown = ttk.Combobox(
            filter_frame, textvariable=self.group_var, state="readonly",
            style="Custom.TCombobox", width=20
        )
        self.group_dropdown.pack(side="left", padx=5, ipadx=5, ipady=6)
        self.group_dropdown.bind("<<ComboboxSelected>>", lambda e: self.update_list())
        
        ttk.Label(filter_frame, text="Date (YYYY or YYYY-MM):").pack(side="left", padx=(20,0))
        self.date_var = tk.StringVar()
        date_entry = tk.Entry(filter_frame, textvariable=self.date_var, width=10, font=FONT_MAIN, bg=DARK_BG, fg=BRIGHT_FG, insertbackground=BRIGHT_FG)
        date_entry.pack(side="left", padx=5, ipadx=5, ipady=3); date_entry.bind("<KeyRelease>", lambda e: self.update_list())
        
        ttk.Label(filter_frame, text="4K?:").pack(side="left", padx=(20,0))
        self.filter_4k_var = tk.BooleanVar(value=False)
        filter_4k_checkbutton = ttk.Checkbutton(filter_frame, variable=self.filter_4k_var, command=self.update_list)
        filter_4k_checkbutton.pack(side="left", padx=(2, 10))
        
        ttk.Label(filter_frame, text="Search:").pack(side="left", padx=(10,0))
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(filter_frame, textvariable=self.search_var, font=FONT_MAIN, bg=DARK_BG, fg=BRIGHT_FG, insertbackground=BRIGHT_FG)
        search_entry.pack(side="left", fill="x", expand=True, padx=5, ipadx=5, ipady=3); search_entry.bind("<KeyRelease>", lambda e: self.update_list())
        
        ttk.Button(filter_frame, text="Clear", command=self.clear_search).pack(side="left", padx=5, ipadx=8, ipady=3)

        header_text = (f"{'Date':<12} | {'Group':<35} | {'Show':<15} | {'Res':<8} | {'Score':<4} | {'Songs':<80} | {'Path'}")
        header = tk.Label(self, text=header_text, font=FONT_HEADER, anchor="w", bg=DARK_BG, fg=BRIGHT_FG)
        header.pack(fill="x", padx=10, pady=(5,0))

        listbox_frame = tk.Frame(self, bg=DARK_BG); listbox_frame.pack(fill="both", expand=True, padx=10, pady=5)
        vscroll = ttk.Scrollbar(listbox_frame, orient="vertical", style="Vertical.TScrollbar") 
        vscroll.pack(side="right", fill="y")
        hscroll = ttk.Scrollbar(listbox_frame, orient="horizontal", style="Horizontal.TScrollbar")
        hscroll.pack(side="bottom", fill="x")
        self.listbox = tk.Listbox(listbox_frame, font=FONT_MAIN, yscrollcommand=vscroll.set, xscrollcommand=hscroll.set, bg=DARK_BG, fg=BRIGHT_FG,
            selectbackground="#44475a", selectforeground="#f1fa8c", highlightbackground=ACCENT, highlightcolor=ACCENT,
            activestyle="none", relief="flat", borderwidth=0, selectmode=tk.EXTENDED)
        self.listbox.pack(side="left", fill="both", expand=True); self.listbox.bind("<Double-Button-1>", lambda e: self.play_selected())
        vscroll.config(command=self.listbox.yview); hscroll.config(command=self.listbox.xview)

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

        status_font = ("Arial", 16, "bold") 
        status = tk.Label(self, textvariable=self.status_var, relief="sunken", anchor="w", font=status_font, bg=ACCENT, fg=BRIGHT_FG, padx=8, pady=6)
        status.pack(fill="x", side="bottom"); self.status_var.set("Ready.")

    def disable_play_buttons(self):
        if self.play_button: self.play_button.config(state=tk.DISABLED)
        if self.play_random_button: self.play_random_button.config(state=tk.DISABLED)

    def enable_play_buttons(self):
        if self.play_button: self.play_button.config(state=tk.NORMAL)
        if self.play_random_button: self.play_random_button.config(state=tk.NORMAL)

    def clear_search(self):
        self.search_var.set(""); self.group_var.set(""); self.date_var.set(""); self.filter_4k_var.set(False)
        self.update_list()

    def load_groups(self):
        cur = self.conn.cursor(); cur.execute("SELECT group_name FROM groups ORDER BY group_name")
        self.groups = [row[0] for row in cur.fetchall()]; self.group_dropdown["values"] = [""] + self.groups

    def load_performances(self):
        self.status_var.set("Loading performances from database..."); self.update_idletasks()
        query = """SELECT performances.performance_id, groups.group_name, performances.performance_date, performances.show_type, performances.resolution, performances.file_path, performances.score, performances.notes FROM performances LEFT JOIN groups ON performances.group_id = groups.group_id ORDER BY performances.performance_date DESC"""
        cur = self.conn.cursor(); cur.execute(query); self.performances = cur.fetchall()
        self.update_list() # update_list will set status
        self.pre_wake_external_drives() # Call after performances are loaded

    def update_list(self):
        group_filter = self.group_var.get().lower(); date_filter = self.date_var.get(); search_filter = self.search_var.get().lower(); filter_4k_enabled = self.filter_4k_var.get()
        self.filtered = []; self.listbox.delete(0, tk.END)
        for perf in self.performances:
            group = perf[1] or ""; date = perf[2] or ""; show = perf[3] or ""; resolution = perf[4] or ""
            score = str(perf[6]) if perf[6] is not None else ""
            songs_data = perf[7] or "" 
            path = perf[5] or ""
            
            if group_filter and group_filter != group.lower(): continue
            if date_filter and not date.startswith(date_filter): continue
            if filter_4k_enabled:
                res_lower = resolution.lower()
                if not any(keyword in res_lower for keyword in self.RESOLUTION_HIGH_QUALITY_KEYWORDS): continue
            
            # Path part in display string will show full path/URL
            display_path = path
            if KpopDBBrowser.is_youtube_url(path):
                display_path = "YouTube Link" # Or keep full URL if preferred, or first 30 chars
            
            # Truncate songs_data for display consistency, path will take remaining space or be truncated by listbox
            songs_display = songs_data[:77] + '...' if len(songs_data) > 80 else songs_data
            
            # Display format updated for potentially long paths/URLs or shorter 'YouTube Link'
            display = f"{date:<12} | {group:<35} | {show:<15} | {resolution:<8} | {score:<4} | {songs_display:<80} | {display_path}"

            if search_filter:
                # Search in all relevant fields, including the original full songs_data and path
                searchable_text = f"{date} {group} {show} {resolution} {score} {songs_data} {path}".lower()
                if search_filter not in searchable_text: continue
            
            self.filtered.append(perf); self.listbox.insert(tk.END, display)
        self.status_var.set(f"{len(self.filtered)} performances match your filters.")

    def play_selected(self):
        if self.play_button and self.play_button.cget('state') == tk.DISABLED:
            self.status_var.set("Playback operation already in progress..."); self.update_idletasks(); return
        
        selected_indices = self.listbox.curselection()
        if not selected_indices: 
            messagebox.showinfo("No selection", "Please select one or more performances to play.", parent=self); return
        
        local_files_to_play = []
        youtube_urls_to_open = []
        all_perf_details_for_callbacks = []
        skipped_items_info = []

        for index_str in selected_indices:
            try:
                perf_index = int(index_str)
                if 0 <= perf_index < len(self.filtered):
                    perf = self.filtered[perf_index]
                    file_path_or_url = perf[5]

                    if not file_path_or_url:
                        skipped_items_info.append(f"No path/URL for: {perf[1] or 'N/A'} ({perf[2] or 'N/A'})")
                        continue
                    
                    is_url = KpopDBBrowser.is_youtube_url(file_path_or_url)
                    if is_url:
                        youtube_urls_to_open.append(file_path_or_url)
                        all_perf_details_for_callbacks.append(perf)
                    else: # Local file
                        if not os.path.exists(file_path_or_url):
                            skipped_items_info.append(f"Local file not found: {os.path.basename(file_path_or_url)}")
                            continue
                        local_files_to_play.append(file_path_or_url)
                        all_perf_details_for_callbacks.append(perf)
            except ValueError: 
                print(f"Warning: Could not parse selection index: {index_str}")
        
        if skipped_items_info: 
            messagebox.showwarning("Playback Warning", "Some items were skipped:\n- " + "\n- ".join(skipped_items_info), parent=self)
        
        if not local_files_to_play and not youtube_urls_to_open:
            self.status_var.set("Ready. No valid items to play from selection.")
            if not skipped_items_info: # Only show if no other warning was given
                 messagebox.showinfo("No Playable Items", "No valid files or YouTube URLs selected for playback.", parent=self)
            return
        
        self.disable_play_buttons()
        
        status_msg = "Preparing playback..."
        if local_files_to_play:
             status_msg = f"Preparing {len(local_files_to_play)} local file(s)"
             if youtube_urls_to_open:
                 status_msg += f" and {len(youtube_urls_to_open)} YouTube URL(s)."
             else:
                 status_msg += "."
        elif youtube_urls_to_open:
            status_msg = f"Preparing {len(youtube_urls_to_open)} YouTube URL(s)."

        self.status_var.set(status_msg); self.update_idletasks()

        thread = threading.Thread(
            target=KpopDBBrowser._execute_playback_sequence_and_callbacks, 
            args=(local_files_to_play, youtube_urls_to_open, all_perf_details_for_callbacks, self, False), # False for is_random_source
            daemon=True
        )
        thread.start()

    def play_random_videos(self):
        if self.play_random_button and self.play_random_button.cget('state') == tk.DISABLED:
            self.status_var.set("Playback operation already in progress..."); self.update_idletasks(); return
        if not self.filtered: 
            messagebox.showinfo("No Videos", "No videos match current filters to play randomly.", parent=self); return
        
        try:
            count_str = self.random_count_var.get()
            num_to_sample = len(self.filtered) if count_str.lower() == "all" else int(count_str)
        except ValueError: 
            messagebox.showerror("Invalid Count", "Please select a valid number of videos.", parent=self); return
        if num_to_sample <= 0: 
            messagebox.showinfo("Invalid Count", "Number of videos must be > 0.", parent=self); return

        actual_num_to_sample = min(num_to_sample, len(self.filtered))
        chosen_perfs_from_sample = random.sample(self.filtered, k=actual_num_to_sample)
        
        local_files_to_play = []
        youtube_urls_to_open = []
        all_perf_details_for_callbacks = []

        for perf in chosen_perfs_from_sample:
            file_path_or_url = perf[5]
            if not file_path_or_url: continue # Silently skip if no path/URL

            is_url = KpopDBBrowser.is_youtube_url(file_path_or_url)
            if is_url:
                youtube_urls_to_open.append(file_path_or_url)
                all_perf_details_for_callbacks.append(perf)
            else: # Local file
                if os.path.exists(file_path_or_url):
                    local_files_to_play.append(file_path_or_url)
                    all_perf_details_for_callbacks.append(perf)
                # else: Silently skip non-existent local file for random play
        
        if not local_files_to_play and not youtube_urls_to_open:
            messagebox.showinfo("No Playable Items", "No valid video files or YouTube URLs found among random selection.", parent=self)
            self.status_var.set("Ready. No valid random items to play."); return
        
        self.disable_play_buttons()
        num_total_items = len(all_perf_details_for_callbacks)
        self.status_var.set(f"Preparing {num_total_items} random item(s)...")
        self.update_idletasks()

        thread = threading.Thread(
            target=KpopDBBrowser._execute_playback_sequence_and_callbacks, 
            args=(local_files_to_play, youtube_urls_to_open, all_perf_details_for_callbacks, self, True), # True for is_random_source
            daemon=True
        )
        thread.start()

    @staticmethod
    def _execute_playback_sequence_and_callbacks(
        local_file_paths_list, youtube_url_list,
        all_processed_perf_details, 
        app_instance, is_random_source
    ):
        if not app_instance.winfo_exists(): return

        if not local_file_paths_list and not youtube_url_list:
            app_instance.after(0, app_instance.enable_play_buttons)
            app_instance.after(0, lambda: app_instance.status_var.set("Ready. Nothing to play."))
            return

        # --- Handle Local Files with MPV ---
        mpv_played_count = 0
        if local_file_paths_list:
            first_local_file_path = local_file_paths_list[0]
            first_local_file_basename = os.path.basename(first_local_file_path)
            num_local_files = len(local_file_paths_list)
            mpv_process = None
            try:
                access_message = f"Accessing local: {first_local_file_basename} (1 of {num_local_files}). Waking drive..."
                if app_instance.winfo_exists(): app_instance.after(0, lambda: app_instance.status_var.set(access_message))
                
                with open(first_local_file_path, "rb") as f: f.read(1) # Pre-access first file

                command = [MPV_PLAYER_PATH] + local_file_paths_list
                mpv_process = subprocess.Popen(command)
                mpv_played_count = num_local_files # Assume all will be attempted by mpv

                if app_instance.winfo_exists():
                    status_msg = f"Playing local: {first_local_file_basename}" if num_local_files == 1 else \
                                 f"Playing {num_local_files} local files (starting with: {first_local_file_basename}). Waiting for player..."
                    app_instance.after(0, lambda: app_instance.status_var.set(status_msg))
                
                mpv_process.wait() # Wait for MPV to finish

                if app_instance.winfo_exists():
                    app_instance.after(0, lambda: app_instance.status_var.set(f"Finished playing {num_local_files} local file(s)."))
            
            except FileNotFoundError: # Covers MPV not found or first_local_file_path not found before Popen
                 if app_instance.winfo_exists():
                    error_msg = f"MPV player not found ('{MPV_PLAYER_PATH}') OR file access error for '{first_local_file_path}'."
                    app_instance.after(0, lambda: messagebox.showerror("Playback Error", error_msg, parent=app_instance))
                    app_instance.after(0, lambda: app_instance.status_var.set(f"Error: {error_msg}"))
                    mpv_played_count = 0 # Reset as it failed
            except Exception as e:
                if app_instance.winfo_exists():
                    error_msg = f"Could not play local files (starting with {first_local_file_path}): {e}"
                    app_instance.after(0, lambda: messagebox.showerror("Playback Error", error_msg, parent=app_instance))
                    app_instance.after(0, lambda: app_instance.status_var.set(f"Error playing local: {e}"))
                    mpv_played_count = 0 # Reset on general error
            finally:
                if mpv_process and mpv_process.poll() is None:
                    try: mpv_process.terminate()
                    except: pass
        
        # --- Handle YouTube URLs ---
        yt_opened_count = 0
        if youtube_url_list:
            num_youtube_urls = len(youtube_url_list)
            if app_instance.winfo_exists():
                app_instance.after(0, lambda: app_instance.status_var.set(f"Opening {num_youtube_urls} YouTube video(s) in browser..."))

            for url in youtube_url_list:
                try:
                    parsed_url = urlparse(url)
                    query_params = parse_qs(parsed_url.query)
                    query_params['autoplay'] = ['1']
                    query_params['rel'] = ['0'] # Optional: disable related videos from other channels
                    # query_params['modestbranding'] = ['1'] # Optional: less YouTube branding (if it works)
                    
                    new_query_string = urlencode(query_params, doseq=True)
                    final_url_parts = list(parsed_url)
                    final_url_parts[4] = new_query_string 
                    final_url = urlunparse(final_url_parts)
                    
                    if webbrowser.open_new_tab(final_url):
                        yt_opened_count += 1
                except webbrowser.Error as e:
                    if app_instance.winfo_exists():
                        app_instance.after(0, lambda u=url, err=e: app_instance.status_var.set(f"Failed to open {u}: {err}"))
                        # Consider a non-blocking warning if many URLs fail
                        # app_instance.after(0, lambda u=url, err=e: messagebox.showwarning("Browser Error", f"Could not open URL {u}:\n{err}", parent=app_instance))
                except Exception as e: # Catch other potential errors during URL processing
                    if app_instance.winfo_exists():
                        app_instance.after(0, lambda u=url, err=e: app_instance.status_var.set(f"Error processing URL {u}: {err}"))


            if app_instance.winfo_exists():
                status_parts = []
                if local_file_paths_list: # If local files were part of this operation
                    status_parts.append(f"{mpv_played_count} local file(s) processed.")
                
                if yt_opened_count == num_youtube_urls:
                    status_parts.append(f"{yt_opened_count} YouTube video(s) opened.")
                else:
                    status_parts.append(f"{yt_opened_count} of {num_youtube_urls} YouTube video(s) opened (some may have failed).")
                
                app_instance.after(0, lambda: app_instance.status_var.set(" ".join(status_parts)))

        # --- Post-Playback Callbacks (common for both local and YouTube) ---
        if app_instance.winfo_exists():
            app_instance.after(100, app_instance.enable_play_buttons) # Enable buttons (slight delay to allow status update)

            if all_processed_perf_details: # Ensure there's something to process for callbacks
                total_items_for_callback = len(all_processed_perf_details)
                
                # Set a slightly delayed final status summarizing the operation
                final_summary_status = f"Playback actions complete for {total_items_for_callback} item(s). "
                if app_instance.change_score_var.get():
                    final_summary_status += "Score editor opening..."
                elif is_random_source:
                    final_summary_status += "Info window opening..."
                else:
                    final_summary_status += "Ready."
                app_instance.after(500, lambda fs=final_summary_status: app_instance.status_var.set(fs))


                if app_instance.change_score_var.get():
                    app_instance.after(600, lambda: app_instance.open_score_editor(all_processed_perf_details, is_random_source))
                elif is_random_source: # Not changing score, but it was random play
                    app_instance.after(600, lambda: app_instance.show_played_info_window(all_processed_perf_details))
            else: # No items were actually processed for callbacks (e.g., all skipped or failed before this stage)
                app_instance.after(500, lambda: app_instance.status_var.set("Ready. No valid items were processed for further actions."))
        
    def show_played_info_window(self, played_details):
        if not played_details: return
        info_window = tk.Toplevel(self); info_window.title("Played Performance Details (Random Selection)"); info_window.geometry("800x450")
        info_window.configure(bg=DARK_BG); info_window.transient(self); info_window.grab_set()
        text_area_frame = ttk.Frame(info_window); text_area_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10,0))
        text_area = tk.Text(text_area_frame, wrap=tk.WORD, font=FONT_MAIN, bg=DARK_BG, fg=BRIGHT_FG, relief="flat", borderwidth=0,
                            selectbackground="#44475a", selectforeground="#f1fa8c", insertbackground=BRIGHT_FG)
        vscroll = ttk.Scrollbar(text_area_frame, orient="vertical", command=text_area.yview, style="Vertical.TScrollbar")
        text_area.configure(yscrollcommand=vscroll.set); vscroll.pack(side="right", fill="y"); text_area.pack(side="left", fill=tk.BOTH, expand=True)
        text_area.insert(tk.END, f"Details of {len(played_details)} randomly played performance(s):\n\n")
        for i, perf in enumerate(played_details):
            group = perf[1] or "N/A"; date = perf[2] or "N/A"; show = perf[3] or "N/A"
            score = str(perf[6]) if perf[6] is not None else "N/A"
            songs_text = perf[7] or "N/A" 
            path_info = perf[5] or "N/A"
            if KpopDBBrowser.is_youtube_url(path_info): path_info = f"YouTube: {path_info}"
            else: path_info = f"File: {path_info}"

            text_area.insert(tk.END, f"{i+1}. Group: {group}\n")
            text_area.insert(tk.END, f"   Date:  {date}\n")
            text_area.insert(tk.END, f"   Show:  {show}\n")
            text_area.insert(tk.END, f"   Score: {score}\n")
            text_area.insert(tk.END, f"   Songs: {songs_text}\n")
            text_area.insert(tk.END, f"   Source: {path_info}\n\n")
        text_area.config(state=tk.DISABLED)
        close_button = ttk.Button(info_window, text="Close", command=info_window.destroy); close_button.pack(pady=10)
        info_window.focus_set()

    def open_score_editor(self, played_performance_details, is_random_source=False):
        if self.score_editor_window and self.score_editor_window.winfo_exists():
            self.score_editor_window.lift(); self.score_editor_window.focus_set()
            messagebox.showwarning("Editor Open", "The score editor window is already open.", parent=self); return
        if not played_performance_details: 
            messagebox.showinfo("No Details", "No performance details available to edit scores.", parent=self); return
        
        editor_title_prefix = "Randomly Played" if is_random_source else "Selected"
        editor_title = f"{editor_title_prefix} Items - Score Editor"
        self.score_editor_window = ScoreEditorWindow(self, editor_title, played_performance_details, self.conn, self.refresh_data_and_ui)

    def refresh_data_and_ui(self):
        # This is called by ScoreEditorWindow on save/cancel that leads to destroy
        # Ensure score_editor_window reference is cleared if it was destroyed by its own methods
        if self.score_editor_window and not self.score_editor_window.winfo_exists():
             self.score_editor_window = None
        elif self.score_editor_window : # If it still exists, destroy it (e.g. called after save)
            self.score_editor_window.destroy_and_clear_master_ref() # This will set self.score_editor_window to None
        
        self.load_performances() # Reloads data and updates list
        self.status_var.set("Scores possibly updated. List refreshed."); self.enable_play_buttons()


    def pre_wake_external_drives(self):
        if not self.performances: 
            # self.status_var.set("No performances loaded for pre-wake.") # Can be noisy if list is empty
            return
        
        # Filter out YouTube URLs and ensure path is not None before calling os.path.dirname
        local_file_paths = [
            perf[5] for perf in self.performances 
            if perf[5] and not KpopDBBrowser.is_youtube_url(perf[5])
        ]
        if not local_file_paths:
            # self.status_var.set("No local file paths found for pre-wake.")
            return

        unique_dirs = sorted(list(set(
            os.path.dirname(path) for path in local_file_paths if os.path.dirname(path)
        )))
        
        if not unique_dirs: 
            # self.status_var.set("Could not identify distinct drive paths for pre-wake.")
            return

        dirs_to_ping = []
        if unique_dirs:
            dirs_to_ping.append(unique_dirs[0])
            if len(unique_dirs) > 2: # If at least 3 unique dirs
                mid_idx = len(unique_dirs) // 2
                # Ensure mid_idx is not same as first and not a subpath of first
                if unique_dirs[mid_idx] != dirs_to_ping[0] and not unique_dirs[mid_idx].startswith(dirs_to_ping[0] + os.sep):
                    dirs_to_ping.append(unique_dirs[mid_idx])
            if len(unique_dirs) > 1: # If at least 2 unique dirs
                last_dir = unique_dirs[-1]
                # Ensure last_dir is not same as first (or mid if mid exists) and not a subpath
                is_new_dir = True
                for existing_dir in dirs_to_ping:
                    if last_dir == existing_dir or last_dir.startswith(existing_dir + os.sep):
                        is_new_dir = False
                        break
                if is_new_dir:
                     dirs_to_ping.append(last_dir)
        
        dirs_to_ping = sorted(list(set(dirs_to_ping))) # Remove duplicates again if logic above allows
        dirs_to_ping = dirs_to_ping[:3] # Limit to a max of 3 pings

        if not dirs_to_ping: 
            # self.status_var.set("No suitable distinct drive paths for pre-wake after filtering.")
            return
            
        display_dirs_str = ", ".join([os.path.basename(p) if os.path.basename(p) else p for p in dirs_to_ping]) # Show dir names
        
        # Check current status to avoid overwriting important messages like "Loading..."
        current_status = self.status_var.get()
        if "Loading" not in current_status and "Playing" not in current_status and "Accessing" not in current_status:
             self.status_var.set(f"Pre-waking drives (e.g., {display_dirs_str})..."); self.update_idletasks()
        
        thread = threading.Thread(target=KpopDBBrowser._execute_pre_wake, args=(dirs_to_ping, self), daemon=True); thread.start()

    @staticmethod
    def _execute_pre_wake(dir_paths, app_instance): 
        if not app_instance.winfo_exists(): return
        woken_count, error_count = 0, 0
        for dir_path in dir_paths:
            try:
                # Ensure it's actually a directory and not a file path mistakenly passed
                # The logic in pre_wake_external_drives should give directory paths.
                if os.path.isdir(dir_path):
                    os.listdir(dir_path) # The actual "wake" operation
                    woken_count += 1
                # else: # It's a file path or does not exist, skip (already handled by os.path.isdir)
            except Exception: 
                error_count += 1
        
        if app_instance.winfo_exists(): # Check again before UI update
            current_status = app_instance.status_var.get()
            # Avoid overwriting critical status messages
            if "Loading" not in current_status and "Playing" not in current_status and "Accessing" not in current_status:
                final_message = f"Pre-wake: {woken_count} paths accessed."
                if error_count > 0: final_message += f" ({error_count} issues)."
                else: final_message += " Ready."
                app_instance.after(0, lambda: app_instance.status_var.set(final_message))


    def on_closing(self): 
        if self.score_editor_window and self.score_editor_window.winfo_exists():
            self.score_editor_window.cancel() # This might destroy it
            if self.score_editor_window and self.score_editor_window.winfo_exists():
                self.score_editor_window.destroy_and_clear_master_ref()
        self.conn.close(); self.destroy()

if __name__ == "__main__":
    app = KpopDBBrowser()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
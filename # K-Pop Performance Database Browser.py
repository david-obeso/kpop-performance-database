# K-Pop Performance Database Browser
# Version 3.2.3 (Score Editor UI Tweaks)
import os
import subprocess
import sqlite3
import sys
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import random

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
        try:
            cursor = self.db_conn.cursor()
            for item_data in self.performance_items_data:
                if item_data["score_var"].get() != item_data["original_score"]:
                    cursor.execute("UPDATE performances SET score = ? WHERE performance_id = ?", 
                                   (item_data["score_var"].get(), item_data["id"]))
                    updates_made += 1
            if updates_made > 0: self.db_conn.commit(); messagebox.showinfo("Success", f"{updates_made} score(s) updated.", parent=self)
            else: messagebox.showinfo("No Changes", "No scores were modified.", parent=self)
        except sqlite3.Error as e:
            self.db_conn.rollback(); messagebox.showerror("Database Error", f"Failed to update scores: {e}", parent=self)
        finally:
            if self.refresh_callback: self.refresh_callback()

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
                ["/home/david/mount_windows_shares.sh"],
                check=False, capture_output=True, text=True
            )
            if process.returncode != 0:
                error_message = f"Could not mount Windows shares!\n\nScript output:\n{process.stdout}\n{process.stderr}\n\nThe program will now exit."
                print(error_message); root_temp = tk.Tk(); root_temp.withdraw(); messagebox.showerror("Mount Error", error_message, parent=None); root_temp.destroy(); sys.exit(1)
            print("Windows shares mounted (or already mounted).")
        except FileNotFoundError:
            error_message = "Mount script '/home/david/mount_windows_shares.sh' not found.\nThe program will now exit."
            print(error_message); root_temp = tk.Tk(); root_temp.withdraw(); messagebox.showerror("Mount Error", error_message, parent=None); root_temp.destroy(); sys.exit(1)
        except Exception as e:
            error_message = f"An unexpected error occurred during mounting: {e}\nThe program will now exit."
            print(error_message); root_temp = tk.Tk(); root_temp.withdraw(); messagebox.showerror("Mount Error", error_message, parent=None); root_temp.destroy(); sys.exit(1)


        super().__init__()
        self.title("K-Pop Performance Database Browser v3.2.2") 
        self.geometry("2100x900")
        self.configure(bg=DARK_BG)

        # Colors for Combobox Listbox (dropdown part)
        combobox_list_bg = '#333a40' # This color will also be used for readonly field background
        combobox_list_select_bg = ACCENT
        combobox_list_select_fg = '#f1fa8c'
        self.option_add('*TCombobox*Listbox.background', combobox_list_bg)
        self.option_add('*TCombobox*Listbox.foreground', BRIGHT_FG)
        self.option_add('*TCombobox*Listbox.selectBackground', combobox_list_select_bg)
        self.option_add('*TCombobox*Listbox.selectForeground', combobox_list_select_fg)
        self.option_add('*TCombobox*Listbox.font', FONT_MAIN) # Dropdown list font
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
        self.currently_playing_random_details = []
        self.change_score_var = tk.BooleanVar(value=False)
        self.score_editor_window = None

        self.create_widgets()
        self.load_groups()
        self.load_performances()
        self.pre_wake_external_drives()

    def create_widgets(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=DARK_BG)
        style.configure("TLabel", background=DARK_BG, foreground=BRIGHT_FG, font=FONT_MAIN)
        
        # Updated TButton style for consistency with ScoreEditorWindow
        style.configure("TButton", background=ACCENT, foreground=BRIGHT_FG, font=FONT_BUTTON)
        style.map("TButton", 
                  background=[("active", "#6272a4"), ("disabled", "#303030")],
                  foreground=[("disabled", "#888888")] # Muted text for disabled button
        )

        # --- MODIFIED Combobox Styling START ---
        # Configure base properties like font and selection appearance for the Combobox field
        style.configure("Custom.TCombobox",
            font=("Courier New", 16, "bold"), # Font for the text in the combobox field
            selectbackground=ACCENT,          # Field background when combobox is focused (ACCENT is #44475a)
            selectforeground=BRIGHT_FG        # Field text color when combobox is focused
        )

        # Map state-specific appearances for the Combobox
        # This is key to ensuring the readonly state looks correct from the start.
        style.map("Custom.TCombobox",
            fieldbackground=[
                ('readonly', '#333a40'),  # Field background for normal readonly state (dark grey)
                ('disabled', '#2a2a2a')   # Field background when disabled (darker, muted)
            ],
            foreground=[
                ('readonly', BRIGHT_FG),   # Text color for normal readonly state (bright)
                ('disabled', '#777777')    # Text color when disabled (muted)
            ],
            background=[ # Affects the dropdown arrow button area
                ('readonly', ACCENT),      # Button area normal state (matches TButton background)
                ('active', '#6272a4'),     # Button area when hovered (matches TButton active state)
                ('disabled', '#303030')    # Button area when disabled (matches TButton disabled state)
            ],
            arrowcolor=[ # Color of the dropdown arrow
                ('readonly', BRIGHT_FG),
                ('active', BRIGHT_FG),     # Arrow color on hover (can be same as readonly)
                ('disabled', '#777777')    # Arrow color when disabled (muted)
            ]
        )
        # --- MODIFIED Combobox Styling END ---
        
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
            filter_frame,
            textvariable=self.group_var,
            state="readonly",
            # font=("Courier New", 16, "bold"), # Font is now set by Custom.TCombobox style
            style="Custom.TCombobox",
            width=20
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
            play_controls_frame,
            textvariable=self.random_count_var,
            values=["1", "2", "3", "5", "10", "All"],
            state="readonly",
            width=5,
            # font=("Courier New", 16, "bold"), # Font is now set by Custom.TCombobox style
            style="Custom.TCombobox"
        )
        self.random_count_dropdown.pack(side="left")
        
        self.change_score_checkbox = ttk.Checkbutton(play_controls_frame, text="Change Score After Play", variable=self.change_score_var)
        self.change_score_checkbox.pack(side="left", padx=(20, 0))

        status_font = ("Arial", 16, "bold") # Explicitly defined font for status bar
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
        cur = self.conn.cursor(); cur.execute(query); self.performances = cur.fetchall(); self.update_list()

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
            
            display = f"{date:<12} | {group:<35} | {show:<15} | {resolution:<8} | {score:<4} | {songs_data:<80} | {path}"
            if search_filter and search_filter not in display.lower(): continue
            self.filtered.append(perf); self.listbox.insert(tk.END, display)
        self.status_var.set(f"{len(self.filtered)} performances match your filters.")

    def play_selected(self):
        if self.play_button and self.play_button.cget('state') == tk.DISABLED:
            self.status_var.set("Playback operation already in progress..."); self.update_idletasks(); return
        selected_indices = self.listbox.curselection()
        if not selected_indices: messagebox.showinfo("No selection", "Please select one or more performances to play.", parent=self); return
        
        files_to_play, skipped_files_info, perfs_for_playback_details = [], [], []
        for index_str in selected_indices:
            try:
                perf_index = int(index_str)
                if 0 <= perf_index < len(self.filtered):
                    perf = self.filtered[perf_index]; file_path = perf[5]
                    if not file_path: skipped_files_info.append(f"No path for: {perf[1] or 'N/A'} ({perf[2] or 'N/A'})"); continue
                    if not os.path.exists(file_path): skipped_files_info.append(f"Not found: {os.path.basename(file_path)}"); continue
                    files_to_play.append(file_path); perfs_for_playback_details.append(perf)
            except ValueError: print(f"Warning: Could not parse selection index: {index_str}")
        
        if skipped_files_info: messagebox.showwarning("Playback Warning", "Some files were skipped:\n- " + "\n- ".join(skipped_files_info), parent=self)
        if not files_to_play:
            self.status_var.set("Ready. No valid files to play from selection.")
            if not skipped_files_info: messagebox.showinfo("No Playable Files", "No valid files selected for playback.", parent=self)
            return
        
        self.disable_play_buttons()
        first_file_basename = os.path.basename(files_to_play[0])
        status_msg = f"Preparing to play {first_file_basename}..." if len(files_to_play) == 1 else f"Preparing {len(files_to_play)} files (starting with {first_file_basename})..."
        self.status_var.set(status_msg); self.update_idletasks()
        thread = threading.Thread(target=self._execute_play_playlist_and_handle_score, args=(files_to_play, perfs_for_playback_details, self), daemon=True)
        thread.start()

    @staticmethod
    def _execute_play_playlist_and_handle_score(file_paths_list, played_perf_details, app_instance):
        if not file_paths_list:
            if app_instance.winfo_exists(): app_instance.after(0, app_instance.enable_play_buttons)
            return
        first_file_path, first_file_basename, num_files, process = file_paths_list[0], os.path.basename(file_paths_list[0]), len(file_paths_list), None
        try:
            access_message = f"Accessing: {first_file_basename} (file 1 of {num_files}). Waking drive..."
            if app_instance.winfo_exists(): app_instance.after(0, lambda: app_instance.status_var.set(access_message))
            with open(first_file_path, "rb") as f: f.read(1)
            command = [MPV_PLAYER_PATH] + file_paths_list; process = subprocess.Popen(command)
            if app_instance.winfo_exists():
                status_msg = f"Playing: {first_file_basename}" if num_files == 1 else f"Playing {num_files} files, starting with: {first_file_basename}. Waiting for player..."
                app_instance.after(0, lambda: app_instance.status_var.set(status_msg))
            process.wait()
            if app_instance.winfo_exists():
                app_instance.after(0, lambda: app_instance.status_var.set(f"Finished playing {num_files} file(s)."))
                if app_instance.change_score_var.get() and played_perf_details:
                    app_instance.after(0, lambda: app_instance.open_score_editor(played_perf_details, is_random_source=False))
        except FileNotFoundError: 
            if app_instance.winfo_exists():
                error_msg = f"File not found: {first_file_path}"
                app_instance.after(0, lambda: messagebox.showerror("File Not Found", error_msg, parent=app_instance))
                app_instance.after(0, lambda: app_instance.status_var.set(f"Error: {error_msg}"))
        except Exception as e:
            if app_instance.winfo_exists():
                error_msg = f"Could not access/play (starting with {first_file_path}): {e}"
                app_instance.after(0, lambda: messagebox.showerror("Error", error_msg, parent=app_instance))
                app_instance.after(0, lambda: app_instance.status_var.set(f"Error playing: {e}"))
        finally:
            if process and process.poll() is None:
                try: process.terminate()
                except: pass
            if app_instance.winfo_exists(): app_instance.after(0, app_instance.enable_play_buttons)

    def play_random_videos(self):
        if self.play_random_button and self.play_random_button.cget('state') == tk.DISABLED:
            self.status_var.set("Playback operation already in progress..."); self.update_idletasks(); return
        if not self.filtered: messagebox.showinfo("No Videos", "No videos match current filters to play randomly.", parent=self); return
        try:
            count_str = self.random_count_var.get()
            num_to_play = len(self.filtered) if count_str.lower() == "all" else int(count_str)
        except ValueError: messagebox.showerror("Invalid Count", "Please select a valid number of videos.", parent=self); return
        if num_to_play <= 0: messagebox.showinfo("Invalid Count", "Number of videos must be > 0.", parent=self); return

        actual_num_to_play = min(num_to_play, len(self.filtered))
        chosen_perfs_all_details = random.sample(self.filtered, k=actual_num_to_play)
        files_to_play, valid_chosen_perfs_details = [], []
        for perf in chosen_perfs_all_details:
            file_path = perf[5]
            if file_path and os.path.exists(file_path):
                files_to_play.append(file_path); valid_chosen_perfs_details.append(perf)
        if not files_to_play:
            messagebox.showinfo("No Playable Files", "No valid video files found among random selection.", parent=self)
            self.status_var.set("Ready. No valid random files to play."); return
        self.disable_play_buttons()
        first_file_basename = os.path.basename(files_to_play[0])
        self.status_var.set(f"Preparing {len(files_to_play)} random videos (starting with {first_file_basename})...")
        self.update_idletasks()
        thread = threading.Thread(target=self._execute_random_play_and_wait, args=(files_to_play, valid_chosen_perfs_details, self), daemon=True)
        thread.start()

    @staticmethod
    def _execute_random_play_and_wait(file_paths_list, chosen_perf_full_details, app_instance):
        if not file_paths_list:
            if app_instance.winfo_exists(): app_instance.after(0, app_instance.enable_play_buttons)
            return
        first_file_path, first_file_basename, num_files, process = file_paths_list[0], os.path.basename(file_paths_list[0]), len(file_paths_list), None
        try:
            access_message = f"Accessing: {first_file_basename} (random 1 of {num_files}). Waking drive..."
            if app_instance.winfo_exists(): app_instance.after(0, lambda: app_instance.status_var.set(access_message))
            with open(first_file_path, "rb") as f: f.read(1)
            command = [MPV_PLAYER_PATH] + file_paths_list; process = subprocess.Popen(command)
            if app_instance.winfo_exists():
                status_msg = f"Playing {num_files} random videos (player open). Waiting for player to close..."
                app_instance.after(0, lambda: app_instance.status_var.set(status_msg))
            process.wait()
            if app_instance.winfo_exists():
                if app_instance.change_score_var.get() and chosen_perf_full_details:
                    app_instance.after(0, lambda: app_instance.open_score_editor(chosen_perf_full_details, is_random_source=True))
                    app_instance.after(0, lambda: app_instance.status_var.set(f"Finished playing {num_files} random videos. Score editor opened."))
                elif chosen_perf_full_details:
                    app_instance.after(0, lambda: app_instance.show_played_info_window(chosen_perf_full_details))
                    app_instance.after(0, lambda: app_instance.status_var.set(f"Finished playing {num_files} random videos. Info window shown."))
                else: app_instance.after(0, lambda: app_instance.status_var.set(f"Finished playing {num_files} random videos."))
        except FileNotFoundError: 
            if app_instance.winfo_exists():
                error_msg = f"File not found (random play): {first_file_path}"
                app_instance.after(0, lambda: messagebox.showerror("File Not Found", error_msg, parent=app_instance))
                app_instance.after(0, lambda: app_instance.status_var.set(f"Error: {error_msg}"))
        except Exception as e:
            if app_instance.winfo_exists():
                error_msg = f"Could not access/play random (starting with {first_file_path}): {e}"
                app_instance.after(0, lambda: messagebox.showerror("Error", error_msg, parent=app_instance))
                app_instance.after(0, lambda: app_instance.status_var.set(f"Error playing random: {e}"))
        finally:
            if process and process.poll() is None:
                try: process.terminate()
                except: pass
            if app_instance.winfo_exists(): app_instance.after(0, app_instance.enable_play_buttons)

    def show_played_info_window(self, played_details):
        if not played_details: return
        info_window = tk.Toplevel(self); info_window.title("Played Performance Details (Random Selection)"); info_window.geometry("800x450")
        info_window.configure(bg=DARK_BG); info_window.transient(self)
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
            text_area.insert(tk.END, f"{i+1}. Group: {group}\n")
            text_area.insert(tk.END, f"   Date:  {date}\n")
            text_area.insert(tk.END, f"   Show:  {show}\n")
            text_area.insert(tk.END, f"   Score: {score}\n")
            text_area.insert(tk.END, f"   Songs: {songs_text}\n\n")
        text_area.config(state=tk.DISABLED)
        close_button = ttk.Button(info_window, text="Close", command=info_window.destroy); close_button.pack(pady=10)

    def open_score_editor(self, played_performance_details, is_random_source=False):
        if self.score_editor_window and self.score_editor_window.winfo_exists():
            self.score_editor_window.lift(); self.score_editor_window.focus_set()
            messagebox.showwarning("Editor Open", "The score editor window is already open.", parent=self); return
        if not played_performance_details: messagebox.showinfo("No Details", "No performance details available to edit scores.", parent=self); return
        editor_title = f"{'Randomly Played' if is_random_source else 'Played'} Performance Score Editor"
        self.score_editor_window = ScoreEditorWindow(self, editor_title, played_performance_details, self.conn, self.refresh_data_and_ui)

    def refresh_data_and_ui(self):
        if self.score_editor_window and self.score_editor_window.winfo_exists(): self.score_editor_window.destroy_and_clear_master_ref()
        self.score_editor_window = None
        self.load_performances()
        self.status_var.set("Scores updated. List refreshed."); self.enable_play_buttons()

    def pre_wake_external_drives(self):
        if not self.performances: self.status_var.set("No performances loaded for pre-wake."); return
        unique_dirs = sorted(list(set(os.path.dirname(perf[5]) for perf in self.performances if perf[5] and os.path.dirname(perf[5]))))
        dirs_to_ping = []
        if unique_dirs:
            dirs_to_ping.append(unique_dirs[0])
            if len(unique_dirs) > 2:
                mid_idx = len(unique_dirs) // 2
                if not unique_dirs[mid_idx].startswith(dirs_to_ping[0]): dirs_to_ping.append(unique_dirs[mid_idx])
            if len(unique_dirs) > 1:
                last_dir = unique_dirs[-1]
                if not last_dir.startswith(dirs_to_ping[0]) and (len(dirs_to_ping) < 2 or not last_dir.startswith(dirs_to_ping[1])): dirs_to_ping.append(last_dir)
        dirs_to_ping = sorted(list(set(dirs_to_ping)))
        if not dirs_to_ping: self.status_var.set("Could not identify distinct drive paths for pre-wake."); return
        display_dirs, display_dirs_str = dirs_to_ping[:3], ", ".join(dirs_to_ping[:3])
        if len(dirs_to_ping) > 3: display_dirs_str += f"... and {len(dirs_to_ping)-3} more"
        self.status_var.set(f"Attempting to pre-wake drives for paths like: {display_dirs_str}..."); self.update_idletasks()
        thread = threading.Thread(target=self._execute_pre_wake, args=(dirs_to_ping, self), daemon=True); thread.start()

    @staticmethod
    def _execute_pre_wake(dir_paths, app_instance): 
        woken_count, error_count = 0, 0
        for dir_path in dir_paths:
            try:
                if not os.path.isdir(dir_path):
                    potential_dir = os.path.dirname(dir_path)
                    if os.path.isdir(potential_dir): dir_path = potential_dir
                    else: continue
                os.listdir(dir_path); woken_count += 1
            except Exception: error_count += 1
        final_message = f"Pre-wake attempt finished. Accessed {woken_count} paths."
        if error_count > 0: final_message += f" Encountered issues with {error_count} paths."
        if app_instance.winfo_exists(): app_instance.after(0, lambda: app_instance.status_var.set(final_message))


    def on_closing(self): 
        if self.score_editor_window and self.score_editor_window.winfo_exists():
            self.score_editor_window.cancel() 
            if self.score_editor_window and self.score_editor_window.winfo_exists(): # Check again as cancel might destroy it
                self.score_editor_window.destroy()
        self.conn.close(); self.destroy()

if __name__ == "__main__":
    app = KpopDBBrowser()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
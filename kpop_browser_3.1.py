# K-Pop Performance Database Browser
# Version 3.1
import os
import subprocess
import sqlite3
import sys
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import random # Import random module

DATABASE_FILE = "kpop_database.db"
MPV_PLAYER_PATH = "mpv"

DARK_BG = "#222222"
BRIGHT_FG = "#f8f8f2"
ACCENT = "#44475a"
FONT_MAIN = ("Courier New", 13)
FONT_HEADER = ("Courier New", 13, "bold")
FONT_STATUS = ("Arial", 13) # Note: Screenshot status bar font seems larger, used Arial 16 bold in code
FONT_BUTTON = ("Arial", 13, "bold")

class KpopDBBrowser(tk.Tk):
    def __init__(self):
        # ... (mounting logic as before) ...
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
        self.title("K-Pop Performance Database Browser")
        self.geometry("2100x900") # Consider adjusting height slightly for new controls
        self.configure(bg=DARK_BG)

        # --- Add these lines to style the Combobox dropdown list ---
        # Use a background similar to the Custom.TCombobox fieldbackground for consistency
        combobox_list_bg = '#333a40'
        # Use selection colors consistent with the main Listbox
        combobox_list_select_bg = ACCENT # which is '#44475a'
        combobox_list_select_fg = '#f1fa8c'

        self.option_add('*TCombobox*Listbox.background', combobox_list_bg)
        self.option_add('*TCombobox*Listbox.foreground', BRIGHT_FG)
        self.option_add('*TCombobox*Listbox.selectBackground', combobox_list_select_bg)
        self.option_add('*TCombobox*Listbox.selectForeground', combobox_list_select_fg)
        self.option_add('*TCombobox*Listbox.font', FONT_MAIN)
        self.option_add('*TCombobox*Listbox.relief', 'flat')
        self.option_add('*TCombobox*Listbox.borderwidth', 0)
        # --- End of new lines for Combobox dropdown styling ---

        self.conn = sqlite3.connect(DATABASE_FILE)
        self.performances = []
        self.filtered = []
        self.groups = []
        self.RESOLUTION_HIGH_QUALITY_KEYWORDS = ["4k", "upscaled", "ai"]
        self.status_var = tk.StringVar(value="Initializing...")

        # For managing play buttons and random play data
        self.play_button = None
        self.play_random_button = None
        self.random_count_var = tk.StringVar()
        self.random_count_dropdown = None
        self.currently_playing_random_details = [] # Stores details for the info window

        self.create_widgets()
        self.load_groups()
        self.load_performances()
        self.pre_wake_external_drives()

    def create_widgets(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        # ... (style configurations as before) ...
        style.configure("TFrame", background=DARK_BG)
        style.configure("TLabel", background=DARK_BG, foreground=BRIGHT_FG, font=FONT_MAIN)
        style.configure("TButton", background=ACCENT, foreground=BRIGHT_FG, font=FONT_BUTTON)
        style.map("TButton", background=[("active", "#6272a4")])
        # General TCombobox style (affects the entry part primarily)
        style.configure("TCombobox", fieldbackground=DARK_BG, background=DARK_BG, foreground=BRIGHT_FG, font=FONT_MAIN)
        # Custom style for the group dropdown (affects its entry part)
        style.configure("Custom.TCombobox", fieldbackground="#333a40", background="#333a40",
                        foreground=BRIGHT_FG, font=("Courier New", 14, "bold"), # Font for entry field
                        selectbackground="#44475a", selectforeground=BRIGHT_FG)
        style.configure("TCheckbutton", background=DARK_BG, foreground=BRIGHT_FG, font=FONT_MAIN)
        style.map("TCheckbutton",
                  indicatorcolor=[('selected', ACCENT), ('!selected', '#555555')],
                  background=[('active', DARK_BG)])


        filter_frame = ttk.Frame(self)
        filter_frame.pack(fill="x", padx=10, pady=8)
        # ... (Group, Date, 4K, Search filters as before) ...
        ttk.Label(filter_frame, text="Group:").pack(side="left")
        self.group_var = tk.StringVar()
        self.group_dropdown = ttk.Combobox(
            filter_frame, textvariable=self.group_var, state="readonly",
            font=("Courier New", 16, "bold"), style="Custom.TCombobox", width=20 # Direct font for entry
        )
        self.group_dropdown.pack(side="left", padx=5, ipadx=5, ipady=6)
        self.group_dropdown.bind("<<ComboboxSelected>>", lambda e: self.update_list())

        ttk.Label(filter_frame, text="Date (YYYY or YYYY-MM):").pack(side="left", padx=(20,0))
        self.date_var = tk.StringVar()
        date_entry = tk.Entry(filter_frame, textvariable=self.date_var, width=10, font=FONT_MAIN, bg=DARK_BG, fg=BRIGHT_FG, insertbackground=BRIGHT_FG)
        date_entry.pack(side="left", padx=5, ipadx=5, ipady=3)
        date_entry.bind("<KeyRelease>", lambda e: self.update_list())

        ttk.Label(filter_frame, text="4K?:").pack(side="left", padx=(20,0))
        self.filter_4k_var = tk.BooleanVar(value=False)
        filter_4k_checkbutton = ttk.Checkbutton(
            filter_frame, variable=self.filter_4k_var, command=self.update_list
        )
        filter_4k_checkbutton.pack(side="left", padx=(2, 10))

        ttk.Label(filter_frame, text="Search:").pack(side="left", padx=(10,0))
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(filter_frame, textvariable=self.search_var, font=FONT_MAIN, bg=DARK_BG, fg=BRIGHT_FG, insertbackground=BRIGHT_FG)
        search_entry.pack(side="left", fill="x", expand=True, padx=5, ipadx=5, ipady=3)
        search_entry.bind("<KeyRelease>", lambda e: self.update_list())
        ttk.Button(filter_frame, text="Clear", command=self.clear_search).pack(side="left", padx=5, ipadx=8, ipady=3)


        header_text = (
            f"{'Date':<12} | {'Group':<35} | {'Show':<15} | {'Res':<8} | {'Score':<4} | {'Songs':<80} | {'Path'}"
        )
        header = tk.Label(self, text=header_text, font=FONT_HEADER, anchor="w", bg=DARK_BG, fg=BRIGHT_FG)
        header.pack(fill="x", padx=10, pady=(5,0))

        listbox_frame = tk.Frame(self, bg=DARK_BG)
        listbox_frame.pack(fill="both", expand=True, padx=10, pady=5)
        # ... (Listbox and scrollbars as before) ...
        vscroll = tk.Scrollbar(listbox_frame, orient="vertical", width=24, bg=ACCENT, activebackground="#6272a4", troughcolor=DARK_BG)
        vscroll.pack(side="right", fill="y")
        hscroll = tk.Scrollbar(listbox_frame, orient="horizontal", width=24, bg=ACCENT, activebackground="#6272a4", troughcolor=DARK_BG)
        hscroll.pack(side="bottom", fill="x")
        self.listbox = tk.Listbox(
            listbox_frame, font=FONT_MAIN, yscrollcommand=vscroll.set,
            xscrollcommand=hscroll.set, bg=DARK_BG, fg=BRIGHT_FG,
            selectbackground="#44475a", selectforeground="#f1fa8c",
            highlightbackground=ACCENT, highlightcolor=ACCENT,
            activestyle="none", relief="flat", borderwidth=0,
            selectmode=tk.EXTENDED
        )
        self.listbox.pack(side="left", fill="both", expand=True)
        self.listbox.bind("<Double-Button-1>", lambda e: self.play_selected())
        vscroll.config(command=self.listbox.yview)
        hscroll.config(command=self.listbox.xview)


        # --- Play Controls Frame (bottom) ---
        play_controls_frame = ttk.Frame(self)
        play_controls_frame.pack(pady=10) # Pack before status bar

        self.play_button = ttk.Button(play_controls_frame, text="Play Selected", command=self.play_selected)
        self.play_button.pack(side="left", padx=(0, 20), ipadx=10, ipady=5) # Add some space after

        self.play_random_button = ttk.Button(play_controls_frame, text="Play Random", command=self.play_random_videos)
        self.play_random_button.pack(side="left", padx=(0, 5), ipadx=10, ipady=5)

        ttk.Label(play_controls_frame, text="Count:").pack(side="left", padx=(10,2))
        self.random_count_var.set("3") # Default value
        self.random_count_dropdown = ttk.Combobox(
            play_controls_frame,
            textvariable=self.random_count_var,
            values=["1", "3", "5", "10", "20", "All"],
            state="readonly",
            width=5,
            font=FONT_MAIN # Using FONT_MAIN for consistency
        )
        # Apply specific style for dropdown if needed, otherwise general TCombobox style applies
        # self.random_count_dropdown.config(style="Custom.TCombobox") # if you want the bolded font
        self.random_count_dropdown.pack(side="left")

        # Status bar
        status = tk.Label(self, textvariable=self.status_var, relief="sunken", anchor="w", font=("Arial", 16, "bold"), bg=ACCENT, fg=BRIGHT_FG, padx=8, pady=6)
        status.pack(fill="x", side="bottom") # Status bar now at the very bottom
        self.status_var.set("Ready.")

    def disable_play_buttons(self):
        if self.play_button: self.play_button.config(state=tk.DISABLED)
        if self.play_random_button: self.play_random_button.config(state=tk.DISABLED)

    def enable_play_buttons(self):
        if self.play_button: self.play_button.config(state=tk.NORMAL)
        if self.play_random_button: self.play_random_button.config(state=tk.NORMAL)

    def clear_search(self):
        # ... (as before) ...
        self.search_var.set(""); self.group_var.set(""); self.date_var.set(""); self.filter_4k_var.set(False)
        self.update_list()

    def load_groups(self):
        # ... (as before) ...
        cur = self.conn.cursor(); cur.execute("SELECT group_name FROM groups ORDER BY group_name")
        self.groups = [row[0] for row in cur.fetchall()]; self.group_dropdown["values"] = [""] + self.groups

    def load_performances(self):
        # ... (as before) ...
        self.status_var.set("Loading performances from database..."); self.update_idletasks()
        query = """SELECT performances.performance_id, groups.group_name, performances.performance_date, performances.show_type, performances.resolution, performances.file_path, performances.score, performances.notes FROM performances LEFT JOIN groups ON performances.group_id = groups.group_id ORDER BY performances.performance_date DESC"""
        cur = self.conn.cursor(); cur.execute(query); self.performances = cur.fetchall(); self.update_list()

    def update_list(self):
        # ... (as before) ...
        group_filter = self.group_var.get().lower(); date_filter = self.date_var.get(); search_filter = self.search_var.get().lower(); filter_4k_enabled = self.filter_4k_var.get()
        self.filtered = []; self.listbox.delete(0, tk.END)
        for perf in self.performances:
            group = perf[1] or ""; date = perf[2] or ""; show = perf[3] or ""; resolution = perf[4] or ""; score = str(perf[6]) if perf[6] is not None else ""; notes = perf[7] or ""; path = perf[5] or ""
            if group_filter and group_filter != group.lower(): continue
            if date_filter and not date.startswith(date_filter): continue
            if filter_4k_enabled:
                res_lower = resolution.lower()
                if not any(keyword in res_lower for keyword in self.RESOLUTION_HIGH_QUALITY_KEYWORDS): continue
            display = f"{date:<12} | {group:<35} | {show:<15} | {resolution:<8} | {score:<4} | {notes:<80} | {path}"
            if search_filter and search_filter not in display.lower(): continue
            self.filtered.append(perf); self.listbox.insert(tk.END, display)
        self.status_var.set(f"{len(self.filtered)} performances match your filters.")


    def play_selected(self):
        if self.play_button and self.play_button.cget('state') == tk.DISABLED:
            self.status_var.set("Playback operation already in progress...")
            self.update_idletasks()
            return
        selected_indices = self.listbox.curselection()
        if not selected_indices:
            messagebox.showinfo("No selection", "Please select one or more performances to play.", parent=self)
            return
        files_to_play, skipped_files_info = [], []
        for index_str in selected_indices:
            try:
                perf_index = int(index_str)
                if 0 <= perf_index < len(self.filtered):
                    perf = self.filtered[perf_index]; file_path = perf[5]
                    if not file_path: skipped_files_info.append(f"No path for: {perf[1] or 'N/A'} ({perf[2] or 'N/A'})"); continue
                    if not os.path.exists(file_path): skipped_files_info.append(f"Not found: {os.path.basename(file_path)}"); continue
                    files_to_play.append(file_path)
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
        thread = threading.Thread(target=self._execute_play_playlist_fire_and_forget, args=(files_to_play, self), daemon=True)
        thread.start()

    @staticmethod
    def _execute_play_playlist_fire_and_forget(file_paths_list, app_instance):
        # (This is the renamed _execute_play_playlist from previous version)
        if not file_paths_list:
            if app_instance.winfo_exists(): app_instance.after(0, app_instance.enable_play_buttons)
            return
        first_file_path, first_file_basename, num_files = file_paths_list[0], os.path.basename(file_paths_list[0]), len(file_paths_list)
        try:
            access_message = f"Accessing: {first_file_basename} (file 1 of {num_files}). Waking drive..."
            if app_instance.winfo_exists(): app_instance.after(0, lambda: app_instance.status_var.set(access_message))
            with open(first_file_path, "rb") as f: f.read(1)
            command = [MPV_PLAYER_PATH] + file_paths_list; subprocess.Popen(command)
            if app_instance.winfo_exists():
                status_msg = f"Playing: {first_file_basename}" if num_files == 1 else f"Playing {num_files} files, starting with: {first_file_basename}"
                app_instance.after(0, lambda: app_instance.status_var.set(status_msg))
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
            if app_instance.winfo_exists(): app_instance.after(0, app_instance.enable_play_buttons)


    def play_random_videos(self):
        if self.play_random_button and self.play_random_button.cget('state') == tk.DISABLED:
            self.status_var.set("Playback operation already in progress..."); self.update_idletasks(); return
        if not self.filtered:
            messagebox.showinfo("No Videos", "No videos match current filters to play randomly.", parent=self); return
        try:
            count_str = self.random_count_var.get()
            num_to_play = len(self.filtered) if count_str.lower() == "all" else int(count_str)
        except ValueError:
            messagebox.showerror("Invalid Count", "Please select a valid number of videos.", parent=self); return
        if num_to_play <= 0:
            messagebox.showinfo("Invalid Count", "Number of videos must be > 0.", parent=self); return

        actual_num_to_play = min(num_to_play, len(self.filtered))
        chosen_perfs = random.sample(self.filtered, k=actual_num_to_play) if count_str.lower() != "all" else random.sample(self.filtered, len(self.filtered)) # random.sample shuffles for "all" too
        
        self.currently_playing_random_details = [] # Clear previous
        files_to_play = []
        for perf in chosen_perfs:
            file_path = perf[5]
            if file_path and os.path.exists(file_path):
                files_to_play.append(file_path)
                self.currently_playing_random_details.append(perf) # Add only if path valid
            # Else: could log or notify about skipped files from random selection here if desired

        if not files_to_play:
            messagebox.showinfo("No Playable Files", "No valid video files found among random selection.", parent=self)
            self.status_var.set("Ready. No valid random files to play."); return

        self.disable_play_buttons()
        first_file_basename = os.path.basename(files_to_play[0])
        self.status_var.set(f"Preparing {len(files_to_play)} random videos (starting with {first_file_basename})...")
        self.update_idletasks()
        thread = threading.Thread(target=self._execute_random_play_and_wait, args=(files_to_play, self.currently_playing_random_details, self), daemon=True)
        thread.start()

    @staticmethod
    def _execute_random_play_and_wait(file_paths_list, chosen_perf_details_for_info, app_instance):
        if not file_paths_list:
            if app_instance.winfo_exists(): app_instance.after(0, app_instance.enable_play_buttons)
            return
        first_file_path, first_file_basename, num_files = file_paths_list[0], os.path.basename(file_paths_list[0]), len(file_paths_list)
        process = None
        try:
            access_message = f"Accessing: {first_file_basename} (random 1 of {num_files}). Waking drive..."
            if app_instance.winfo_exists(): app_instance.after(0, lambda: app_instance.status_var.set(access_message))
            with open(first_file_path, "rb") as f: f.read(1) # Wake drive

            command = [MPV_PLAYER_PATH] + file_paths_list
            process = subprocess.Popen(command)
            if app_instance.winfo_exists():
                status_msg = f"Playing {num_files} random videos (player open). Waiting for player to close..."
                app_instance.after(0, lambda: app_instance.status_var.set(status_msg))
            
            process.wait() # Block THIS THREAD until mpv finishes

            # MPV finished
            if app_instance.winfo_exists():
                app_instance.after(0, lambda: app_instance.show_played_info_window(chosen_perf_details_for_info))
                app_instance.after(0, lambda: app_instance.status_var.set(f"Finished playing {num_files} random videos. Info window shown."))
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
            if process and process.poll() is None: # If Popen succeeded but thread is exiting (e.g. main app closed)
                try: process.terminate() # Try to clean up mpv
                except: pass
            if app_instance.winfo_exists(): app_instance.after(0, app_instance.enable_play_buttons)

    def show_played_info_window(self, played_details):
        if not played_details: return

        info_window = tk.Toplevel(self)
        info_window.title("Played Performance Details")
        info_window.geometry("800x450") # Slightly taller for button
        info_window.configure(bg=DARK_BG)
        info_window.transient(self) # Keep on top of main window
        # info_window.grab_set() # Uncomment if you want it to be fully modal

        text_area_frame = ttk.Frame(info_window)
        text_area_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10,0))

        text_area = tk.Text(text_area_frame, wrap=tk.WORD, font=FONT_MAIN,
                            bg=DARK_BG, fg=BRIGHT_FG, relief="flat", borderwidth=0,
                            selectbackground="#44475a", selectforeground="#f1fa8c",
                            insertbackground=BRIGHT_FG)
        vscroll = ttk.Scrollbar(text_area_frame, orient="vertical", command=text_area.yview)
        text_area.configure(yscrollcommand=vscroll.set)
        vscroll.pack(side="right", fill="y")
        text_area.pack(side="left", fill=tk.BOTH, expand=True)

        text_area.insert(tk.END, f"Details of {len(played_details)} randomly played performance(s):\n\n")
        for i, perf in enumerate(played_details): # perf is the full tuple
            group = perf[1] or "N/A"; date = perf[2] or "N/A"; show = perf[3] or "N/A"
            score = str(perf[6]) if perf[6] is not None else "N/A"; notes = perf[7] or "N/A"
            text_area.insert(tk.END, f"{i+1}. Group: {group}\n")
            text_area.insert(tk.END, f"   Date:  {date}\n")
            text_area.insert(tk.END, f"   Show:  {show}\n")
            text_area.insert(tk.END, f"   Score: {score}\n")
            text_area.insert(tk.END, f"   Songs: {notes}\n\n")
        text_area.config(state=tk.DISABLED) # Read-only

        close_button = ttk.Button(info_window, text="Close", command=info_window.destroy)
        close_button.pack(pady=10)
        # if info_window.grab_status(): info_window.protocol("WM_DELETE_WINDOW", lambda: (info_window.grab_release(), info_window.destroy()))

    def pre_wake_external_drives(self):
        # ... (as before) ...
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
        # ... (as before) ...
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
        self.conn.close(); self.destroy()

if __name__ == "__main__":
    app = KpopDBBrowser()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
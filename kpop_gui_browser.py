import os
import subprocess
import sqlite3
import sys
import tkinter as tk
from tkinter import ttk, messagebox

DATABASE_FILE = "kpop_database.db"
MPV_PLAYER_PATH = "mpv"

DARK_BG = "#222222"
BRIGHT_FG = "#f8f8f2"
ACCENT = "#44475a"
FONT_MAIN = ("Courier New", 13)
FONT_HEADER = ("Courier New", 13, "bold")
FONT_STATUS = ("Arial", 13)
FONT_BUTTON = ("Arial", 13, "bold")

class KpopDBBrowser(tk.Tk):
    def __init__(self):
        # Mount Windows shares before anything else
        try:
            self.status_message = "Mounting Windows shares, please enter your password if prompted..."
            print(self.status_message)
            subprocess.run(
                ["/home/david/mount_windows_shares.sh"],
                check=True
            )
        except subprocess.CalledProcessError as e:
            tk.messagebox.showerror(
                "Mount Error",
                f"Could not mount Windows shares!\n\nError: {e}\n\nThe program will now exit."
            )
            sys.exit(1)

        super().__init__()
        self.title("K-Pop Performance Database Browser")
        self.geometry("2100x900")
        self.configure(bg=DARK_BG)
        self.conn = sqlite3.connect(DATABASE_FILE)
        self.performances = []
        self.filtered = []
        self.groups = []
        self.create_widgets()
        self.load_groups()
        self.load_performances()

    def create_widgets(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=DARK_BG)
        style.configure("TLabel", background=DARK_BG, foreground=BRIGHT_FG, font=FONT_MAIN)
        style.configure("TButton", background=ACCENT, foreground=BRIGHT_FG, font=FONT_BUTTON)
        style.configure("TCombobox", fieldbackground=DARK_BG, background=DARK_BG, foreground=BRIGHT_FG, font=FONT_MAIN)
        style.map("TButton", background=[("active", "#6272a4")])

        # --- Filter Frame ---
        filter_frame = ttk.Frame(self)
        filter_frame.pack(fill="x", padx=10, pady=8)

        # Group dropdown
        ttk.Label(filter_frame, text="Group:").pack(side="left")
        self.group_var = tk.StringVar()
        # Custom style for Combobox
        style.configure(
            "Custom.TCombobox",
            fieldbackground="#333a40",  # Entry field background
            background="#333a40",       # Dropdown background
            foreground=BRIGHT_FG,
            font=("Courier New", 14, "bold"),
            selectbackground="#44475a",
            selectforeground=BRIGHT_FG,
        )
        self.group_dropdown = ttk.Combobox(
            filter_frame,
            textvariable=self.group_var,
            state="readonly",
            font=("Courier New", 16, "bold"),
            style="Custom.TCombobox",
            width=10  
        )
        self.group_dropdown.pack(side="left", padx=5, ipadx=5, ipady=6)
        self.group_dropdown.bind("<<ComboboxSelected>>", lambda e: self.update_list())

        # Date entry
        ttk.Label(filter_frame, text="Date (YYYY or YYYY-MM):").pack(side="left", padx=(20,0))
        self.date_var = tk.StringVar()
        date_entry = tk.Entry(filter_frame, textvariable=self.date_var, width=14, font=FONT_MAIN, bg=DARK_BG, fg=BRIGHT_FG, insertbackground=BRIGHT_FG)
        date_entry.pack(side="left", padx=5, ipadx=5, ipady=3)
        date_entry.bind("<KeyRelease>", lambda e: self.update_list())

        # General search
        ttk.Label(filter_frame, text="Search:").pack(side="left", padx=(20,0))
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(filter_frame, textvariable=self.search_var, font=FONT_MAIN, bg=DARK_BG, fg=BRIGHT_FG, insertbackground=BRIGHT_FG)
        search_entry.pack(side="left", fill="x", expand=True, padx=5, ipadx=5, ipady=3)
        search_entry.bind("<KeyRelease>", lambda e: self.update_list())
        ttk.Button(filter_frame, text="Clear", command=self.clear_search).pack(side="left", padx=5, ipadx=8, ipady=3)

        # --- Column Headers ---
        header_text = (
            f"{'Date':<12} | {'Group':<35} | {'Show':<15} | {'Res':<8} | {'Score':<4} | {'Notes':<80} | {'Path'}"
        )
        header = tk.Label(self, text=header_text, font=FONT_HEADER, anchor="w",
                          bg=DARK_BG, fg=BRIGHT_FG)
        header.pack(fill="x", padx=10, pady=(5,0))

        # --- Results List with Scrollbars ---
        listbox_frame = tk.Frame(self, bg=DARK_BG)
        listbox_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Vertical scrollbar
        vscroll = tk.Scrollbar(
            listbox_frame,
            orient="vertical",
            width=24,
            bg=ACCENT,                # scrollbar background color
            activebackground="#6272a4",  # color when hovered/active
            troughcolor=DARK_BG       # color of the trough (track)
        )
        vscroll.pack(side="right", fill="y")

        # Horizontal scrollbar
        hscroll = tk.Scrollbar(
            listbox_frame,
            orient="horizontal",
            width=24,
            bg=ACCENT,
            activebackground="#6272a4",
            troughcolor=DARK_BG
        )
        hscroll.pack(side="bottom", fill="x")

        self.listbox = tk.Listbox(
            listbox_frame,
            font=FONT_MAIN,
            yscrollcommand=vscroll.set,
            xscrollcommand=hscroll.set,
            bg=DARK_BG,
            fg=BRIGHT_FG,
            selectbackground="#44475a",
            selectforeground="#f1fa8c",
            highlightbackground=ACCENT,
            highlightcolor=ACCENT,
            activestyle="none",
            relief="flat",
            borderwidth=0,
        )
        self.listbox.pack(side="left", fill="both", expand=True)
        self.listbox.bind("<Double-Button-1>", lambda e: self.play_selected())

        vscroll.config(command=self.listbox.yview)
        hscroll.config(command=self.listbox.xview)

        # Play button
        play_btn = ttk.Button(self, text="Play Selected", command=self.play_selected)
        play_btn.pack(pady=10, ipadx=10, ipady=5)

        # Status bar
        self.status_var = tk.StringVar(value="Ready.")
        status = tk.Label(self, textvariable=self.status_var, relief="sunken", anchor="w",
                          font=FONT_STATUS, bg=ACCENT, fg=BRIGHT_FG, padx=8, pady=6)
        status.pack(fill="x", side="bottom")

    def clear_search(self):
        self.search_var.set("")
        self.group_var.set("")
        self.date_var.set("")
        self.update_list()

    def load_groups(self):
        cur = self.conn.cursor()
        cur.execute("SELECT group_name FROM groups ORDER BY group_name")
        self.groups = [row[0] for row in cur.fetchall()]
        self.group_dropdown["values"] = [""] + self.groups  # "" for no filter

    def load_performances(self):
        query = """
        SELECT
            performances.performance_id,
            groups.group_name,
            performances.performance_date,
            performances.show_type,
            performances.resolution,
            performances.file_path,
            performances.score,
            performances.notes
        FROM performances
        LEFT JOIN groups ON performances.group_id = groups.group_id
        ORDER BY performances.performance_date DESC
        """
        cur = self.conn.cursor()
        cur.execute(query)
        self.performances = cur.fetchall()
        self.update_list()

    def update_list(self):
        group_filter = self.group_var.get().lower()
        date_filter = self.date_var.get()
        search_filter = self.search_var.get().lower()
        self.filtered = []
        self.listbox.delete(0, tk.END)
        for perf in self.performances:
            # perf: (id, group, date, show, res, path, score, notes)
            group = perf[1] or ""
            date = perf[2] or ""
            show = perf[3] or ""
            res = perf[4] or ""
            score = str(perf[6]) if perf[6] is not None else ""
            notes = perf[7] or ""
            path = perf[5] or ""
            # Adjust field widths as needed for your data
            display = f"{date:<12} | {group:<35} | {show:<15} | {res:<8} | {score:<4} | {notes:<80} | {path}"
            # Apply filters
            if group_filter and group_filter != group.lower():
                continue
            if date_filter and date_filter not in date:
                continue
            if search_filter and search_filter not in display.lower():
                continue
            self.filtered.append(perf)
            self.listbox.insert(tk.END, display)
        self.status_var.set(f"{len(self.filtered)} performances match your filters.")

    def play_selected(self):
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showinfo("No selection", "Please select a performance to play.")
            return
        perf = self.filtered[selection[0]]
        file_path = perf[5]
        if not file_path or not os.path.exists(file_path):
            messagebox.showerror("File not found", f"The file does not exist:\n{file_path}")
            return
        # Show waiting message before accessing the file
        self.status_var.set("Waking up external drive, please wait...")
        self.update_idletasks()  # Force update of the status bar

        try:
            # Try to open the file for reading to trigger drive spin-up
            with open(file_path, "rb"):
                pass
        except Exception as e:
            messagebox.showerror("Error", f"Could not access file: {e}")
            return

        try:
            subprocess.Popen([MPV_PLAYER_PATH, file_path])
            self.status_var.set(f"Playing: {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not launch mpv: {e}")

    def on_closing(self):
        self.conn.close()
        self.destroy()

if __name__ == "__main__":
    app = KpopDBBrowser()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
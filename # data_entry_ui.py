# data_entry_ui.py
import tkinter as tk
from tkinter import ttk, messagebox

# Modularized imports (will be needed later)
# import config
# import utils
# import db_operations

# Constants
DARK_BG = "#222222"
BRIGHT_FG = "#f8f8f2"
ACCENT = "#44475a"
FONT_MAIN = ("Courier New", 13)
FONT_HEADER = ("Courier New", 13, "bold")
FONT_BUTTON = ("Arial", 13, "bold")
# Font for entry widgets in this UI specifically
FONT_ENTRY_DATA_UI = ("Courier New", 13)


class DataEntryWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Add or Modify Database Entry")
        self.geometry("700x550") # Slightly larger for more content
        self.configure(bg=DARK_BG)
        self.transient(master)
        self.grab_set()

        self.master_app = master

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
        # Style for Entry widgets within this Toplevel
        style.configure("DataEntry.TEntry",
                        fieldbackground=DARK_BG, # Background of the text area
                        foreground=BRIGHT_FG,    # Text color
                        insertcolor=BRIGHT_FG,   # Cursor color
                        font=FONT_ENTRY_DATA_UI,
                        borderwidth=1,
                        relief=tk.SOLID) # Or tk.FLAT
        style.map("DataEntry.TEntry",
                  bordercolor=[('focus', '#6272a4'), ('!focus', ACCENT)],
                  relief=[('focus', tk.SOLID), ('!focus', tk.SOLID)])


        main_frame = ttk.Frame(self, padding="20", style="DataEntry.TFrame")
        main_frame.pack(fill=tk.BOTH, expand=True)

        self.entry_type_var = tk.StringVar(value="performance")
        self.source_type_var = tk.StringVar(value="url")

        # --- Top selection frames ---
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
        
        # --- Dynamic content area ---
        # Using a LabelFrame for better visual grouping of the dynamic content
        self.content_area_frame = ttk.LabelFrame(main_frame, text="3. Enter Details", style="DataEntry.TFrame", padding=(10,10))
        self.content_area_frame.pack(pady=10, fill=tk.BOTH, expand=True)
        
        # Initial placeholder in content_area_frame
        self.current_content_placeholder_label = ttk.Label(self.content_area_frame, text="Select options above and click 'Proceed'.", style="DataEntry.TLabel")
        self.current_content_placeholder_label.pack(padx=10, pady=20, anchor="center")

        # Variables for new input fields (will be created dynamically)
        self.url_entry_var = tk.StringVar()


        # --- Action Buttons ---
        button_frame = ttk.Frame(main_frame, style="DataEntry.TFrame")
        button_frame.pack(fill="x", pady=(10, 0), side=tk.BOTTOM) # Reduced top padding

        self.proceed_button = ttk.Button(button_frame, text="Proceed / Next Step", command=self.handle_proceed, style="DataEntry.TButton")
        self.proceed_button.pack(side=tk.RIGHT, padx=5)

        self.cancel_button = ttk.Button(button_frame, text="Cancel", command=self.close_window, style="DataEntry.TButton")
        self.cancel_button.pack(side=tk.RIGHT, padx=5)
        
        self.protocol("WM_DELETE_WINDOW", self.close_window)
        self.focus_set()

    def reset_content_on_selection_change(self):
        """Clears the content area when radio button selections change, prompting user to click Proceed."""
        # print("DEBUG: Selection changed, resetting content area.")
        for widget in self.content_area_frame.winfo_children():
            widget.destroy()
        self.current_content_placeholder_label = ttk.Label(self.content_area_frame, text="Selections changed. Click 'Proceed / Next Step'.", style="DataEntry.TLabel")
        self.current_content_placeholder_label.pack(padx=10, pady=20, anchor="center")
        # Optionally, disable proceed button or change its text until proceed is clicked again.
        # For now, just resetting the view is enough.

    def handle_proceed(self):
        entry_type = self.entry_type_var.get()
        source_type = self.source_type_var.get()
        
        # Clear previous content from content_area_frame
        for widget in self.content_area_frame.winfo_children():
            widget.destroy()

        print(f"Proceeding with: Entry={entry_type}, Source={source_type}")

        if entry_type == "performance" and source_type == "url":
            self.build_performance_url_ui()
        elif entry_type == "music_video" and source_type == "url":
            self.build_music_video_url_ui()
        # Add more elif for "local_file" later
        else:
            # Placeholder for other combinations
            ttk.Label(self.content_area_frame,
                      text=f"Placeholder UI for:\nEntry Type: {entry_type.replace('_', ' ').title()}\nSource Type: {source_type.replace('_', ' ').title()}",
                      style="DataEntry.TLabel", justify=tk.LEFT).pack(padx=10, pady=20, anchor="w")

    def build_performance_url_ui(self):
        """Builds UI for entering Performance details from a URL."""
        # Specific frame for this step, helps in clearing/rebuilding
        step_frame = ttk.Frame(self.content_area_frame, style="DataEntry.TFrame")
        step_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        ttk.Label(step_frame, text="Enter Performance URL:", style="DataEntry.TLabel").pack(anchor="w", pady=(0,2))
        
        url_entry = ttk.Entry(step_frame, textvariable=self.url_entry_var, width=70, style="DataEntry.TEntry")
        url_entry.pack(fill="x", pady=(0,10))
        url_entry.focus_set() # Focus on the URL entry

        # "Check URL" button (placeholder action for now)
        check_url_button = ttk.Button(step_frame, text="Check URL", command=self.check_entered_url, style="DataEntry.TButton")
        check_url_button.pack(anchor="w", pady=5)

        ttk.Label(step_frame, text="Next: Artist Selection...", style="DataEntry.TLabel").pack(anchor="w", pady=(10,0))
        # Future: Add artist selection widgets here

    def build_music_video_url_ui(self):
        """Builds UI for entering Music Video details from a URL."""
        step_frame = ttk.Frame(self.content_area_frame, style="DataEntry.TFrame")
        step_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        ttk.Label(step_frame, text="Enter Music Video URL:", style="DataEntry.TLabel").pack(anchor="w", pady=(0,2))
        
        url_entry = ttk.Entry(step_frame, textvariable=self.url_entry_var, width=70, style="DataEntry.TEntry")
        url_entry.pack(fill="x", pady=(0,10))
        url_entry.focus_set()

        check_url_button = ttk.Button(step_frame, text="Check URL", command=self.check_entered_url, style="DataEntry.TButton")
        check_url_button.pack(anchor="w", pady=5)

        ttk.Label(step_frame, text="Next: Artist Selection...", style="DataEntry.TLabel").pack(anchor="w", pady=(10,0))

    def check_entered_url(self):
        url = self.url_entry_var.get()
        if not url:
            messagebox.showwarning("Input Required", "Please enter a URL.", parent=self)
            return
        
        # Simple check for now, later can use webbrowser or mpv
        if url.startswith("http://") or url.startswith("https://"):
            messagebox.showinfo("URL Check", f"URL seems valid (starts with http/https):\n{url}", parent=self)
            # Here you could try: webbrowser.open_new_tab(url)
        else:
            messagebox.showerror("URL Check", f"URL does not seem valid:\n{url}", parent=self)
        print(f"Checking URL: {url}")


    def close_window(self):
        if hasattr(self.master_app, 'data_entry_window_instance') and \
           self.master_app.data_entry_window_instance == self:
            self.master_app.data_entry_window_instance = None
        self.destroy()
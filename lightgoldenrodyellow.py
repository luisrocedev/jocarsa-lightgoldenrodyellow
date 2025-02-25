import os
import re
import json
import sqlite3
import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk  # Using ttkbootstrap for theming

# Configuration and constants
CONFIG_FILE = "config.json"
ALLOWED_EXTENSIONS = ('.html', '.css', '.js', '.php', '.py','.java')
EXCLUDED_DIRS = {'.git', 'node_modules'}

def load_config():
    """Load configuration from CONFIG_FILE or return defaults."""
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_config(config):
    """Save the configuration to CONFIG_FILE."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print("Error saving config:", e)

config = load_config()

# Global variables to store selections
selected_folder = None
selected_db = None

def build_directory_map(root_path):
    """
    Recursively builds a tree-style view of the project structure using
    Unicode box-drawing characters.
    """
    lines = []
    root_abs = os.path.abspath(root_path)
    lines.append(root_abs)

    def inner(dir_path, prefix=""):
        try:
            entries = sorted(os.listdir(dir_path))
        except Exception:
            return
        # Filter out excluded directories when encountered as directories.
        entries = [e for e in entries if not (os.path.isdir(os.path.join(dir_path, e)) and e in EXCLUDED_DIRS)]
        for i, entry in enumerate(entries):
            full_path = os.path.join(dir_path, entry)
            connector = "└── " if i == len(entries) - 1 else "├── "
            lines.append(prefix + connector + entry)
            if os.path.isdir(full_path):
                extension = "    " if i == len(entries) - 1 else "│   "
                inner(full_path, prefix + extension)
    inner(root_path)
    return "\n".join(lines)

def parse_files(root_path):
    """
    Parse files with allowed extensions and return a list of tuples (file_path, content).
    """
    parsed_files = []
    for dirpath, dirnames, filenames in os.walk(root_path):
        # Exclude specified directories
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]
        for filename in filenames:
            if filename.lower().endswith(ALLOWED_EXTENSIONS):
                file_path = os.path.join(dirpath, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                except Exception as e:
                    content = f"Error reading file: {e}"
                parsed_files.append((file_path, content))
    return parsed_files

def generate_code_report(root_path):
    """
    Generate a code analysis report that includes a tree-view directory map
    and the content of parsed files.
    """
    report_lines = []
    report_lines.append("Project Directory Map:")
    report_lines.append("----------------------")
    report_lines.append(build_directory_map(root_path))
    
    report_lines.append("\nParsed Files:")
    report_lines.append("-------------")
    parsed_files = parse_files(root_path)
    for file_path, content in parsed_files:
        header = f"\nFile: {file_path}\n" + "-" * (len("File: " + file_path))
        report_lines.append(header)
        report_lines.append(content)
    
    return "\n".join(report_lines)

def analyze_single_database(db_path):
    """
    Analyze a single SQLite database file and extract its tables and column information.
    """
    db_details = f"Database: {db_path}"
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        table_details = []
        for table in tables:
            table_name = table[0]
            table_details.append(f"    Table: {table_name}")
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            for col in columns:
                table_details.append(f"        Column: {col[1]} ({col[2]})")
        conn.close()
        return db_details + "\n" + "\n".join(table_details)
    except Exception as e:
        return db_details + f"\n    Error reading database: {e}"

def select_project_folder():
    """
    Let the user select the project folder and store it globally.
    """
    global selected_folder
    initial_dir = config.get("last_code_folder", os.getcwd())
    folder = filedialog.askdirectory(title="Select Project Folder", initialdir=initial_dir)
    if folder:
        selected_folder = folder
        config["last_code_folder"] = folder
        save_config(config)
        messagebox.showinfo("Project Folder Selected", f"Selected folder:\n{folder}")
    return folder

def select_database_file():
    """
    Let the user select a SQLite database file and store it globally.
    """
    global selected_db
    initial_dir = config.get("last_db_folder", os.getcwd())
    file_path = filedialog.askopenfilename(
        title="Select SQLite Database",
        initialdir=initial_dir,
        filetypes=[("SQLite Database", "*.sqlite *.db *.sqlite3"), ("All Files", "*.*")]
    )
    if file_path:
        selected_db = file_path
        config["last_db_folder"] = os.path.dirname(file_path)
        save_config(config)
        messagebox.showinfo("Database Selected", f"Selected database:\n{file_path}")
    return file_path

def generate_combined_report():
    """
    Generate a combined report that joins the code analysis and database analysis.
    """
    if not selected_folder:
        messagebox.showerror("Error", "No project folder selected.")
        return

    code_report = generate_code_report(selected_folder)

    combined_report_lines = []
    combined_report_lines.append("===== CODE ANALYSIS REPORT =====")
    combined_report_lines.append(code_report)

    if selected_db:
        db_report = analyze_single_database(selected_db)
        combined_report_lines.append("\n===== DATABASE ANALYSIS REPORT =====")
        combined_report_lines.append(db_report)
    else:
        combined_report_lines.append("\n===== DATABASE ANALYSIS REPORT =====")
        combined_report_lines.append("No SQLite database selected.")

    combined_report = "\n".join(combined_report_lines)

    # Display the combined report in a new window with a scrollable Text widget.
    report_window = tk.Toplevel(root)
    report_window.title("Combined Analysis Report")

    text_frame = ttk.Frame(report_window)
    text_frame.pack(fill="both", expand=True, padx=10, pady=10)

    text_widget = tk.Text(text_frame, wrap="none")
    text_widget.insert("1.0", combined_report)
    text_widget.pack(side=tk.LEFT, fill="both", expand=True)

    scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
    scrollbar.pack(side=tk.RIGHT, fill="y")
    text_widget.config(yscrollcommand=scrollbar.set)

    btn_frame = ttk.Frame(report_window)
    btn_frame.pack(pady=5)

    save_button = ttk.Button(btn_frame, text="Save Report",
                             command=lambda: save_report(combined_report, selected_folder))
    save_button.pack(side=tk.LEFT, padx=5)

    copy_button = ttk.Button(btn_frame, text="Copy Report",
                             command=lambda: copy_report(combined_report))
    copy_button.pack(side=tk.LEFT, padx=5)




def save_report(report_text, initial_dir):
    """
    Open a dialog to save the report as a text file.
    """
    file_path = filedialog.asksaveasfilename(initialdir=initial_dir,
                                             title="Save Report",
                                             defaultextension=".txt",
                                             filetypes=[("Text Files", "*.txt")])
    if file_path:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(report_text)
            messagebox.showinfo("Success", f"Report saved to {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save report: {e}")

def copy_report(report_text):
    """
    Copy the given report text to the clipboard.
    """
    root.clipboard_clear()
    root.clipboard_append(report_text)
    messagebox.showinfo("Clipboard", "Report copied to clipboard!")



# Set up the main window using ttkbootstrap
style = ttk.Style('flatly')
root = style.master
root.title("Project and Database Analyzer")
root.geometry("400x350")

# Load and display the image
image_path = "lightgoldenrodyellow.png"
try:
    img = tk.PhotoImage(file=image_path)
    image_label = ttk.Label(root, image=img)
    image_label.pack(pady=10)
except Exception as e:
    print(f"Error loading image: {e}")

# Main button layout
main_frame = ttk.Frame(root)
main_frame.pack(expand=True, padx=20, pady=20)

btn_select_folder = ttk.Button(main_frame, text="Select Project Folder", command=select_project_folder)
btn_select_folder.pack(pady=5, fill='x')

# Update the button text to indicate that database selection is optional
btn_select_db = ttk.Button(main_frame, text="Select SQLite Database (Optional)", command=select_database_file)
btn_select_db.pack(pady=5, fill='x')

btn_generate_report = ttk.Button(main_frame, text="Generate Combined Report", command=generate_combined_report)
btn_generate_report.pack(pady=5, fill='x')

root.mainloop()

#!/usr/bin/env python3
import curses
import sqlite3
import json
import os
import subprocess
import shutil
import sys
from urllib.parse import urlparse, unquote
CONFIG_DIR = os.path.expanduser("~/.config/vscode_launcher")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"pinned": [], "mode": "insiders"}
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except:
        return {"pinned": [], "mode": "insiders"}

def save_config(config):
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

# Dynamic Home Path
HOME = os.path.expanduser("~")

# Known IDE configurations
KNOWN_IDES = [
    {"id": "code", "config": "Code", "cmd": "code", "label": "VS Code"},
    {"id": "insiders", "config": "Code - Insiders", "cmd": "code-insiders", "label": "VS Code Insiders"},
    {"id": "antigravity", "config": "Antigravity", "cmd": "antigravity", "label": "Antigravity"},
    {"id": "cursor", "config": "Cursor", "cmd": "cursor", "label": "Cursor"},
    {"id": "vscodium", "config": "VSCodium", "cmd": "codium", "label": "VSCodium"},
]

def discover_ides():
    valid_modes = {}
    valid_dbs = []
    mode_order = []
    
    for ide in KNOWN_IDES:
        config_path = os.path.join(HOME, ".config", ide["config"])
        db_path = os.path.join(config_path, "User", "globalStorage", "state.vscdb")
        
        # Check if config/db exists to consider it for history
        if os.path.exists(config_path):
             if os.path.exists(db_path):
                 valid_dbs.append(db_path)
             
             # Check if binary exists to allow launching
             # We rely on shutil.which to find it in PATH
             if shutil.which(ide["cmd"]):
                 valid_modes[ide["id"]] = {
                     "cmd": ide["cmd"],
                     "label": ide["label"]
                 }
                 mode_order.append(ide["id"])
    
    # Fallback if nothing found?
    if not valid_modes:
        # Defaults just in case avoiding crash
        pass

    return valid_modes, mode_order, valid_dbs

# Initialize discovery
MODES, MODE_ORDER, ALL_DB_PATHS = discover_ides()

# If no modes found, provide a dummy one to avoid crash or loop issues
if not MODES:
    MODES = {"code": {"cmd": "code", "label": "VS Code"}}
    MODE_ORDER = ["code"]

def get_projects(mode=None):
    # Mode argument is kept for compatibility but ignored for DB fetching 
    # as we now aggregate ALL known DBs.
    projects_list = []
    seen = set()
    
    for db_path in ALL_DB_PATHS:
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM ItemTable WHERE key = 'history.recentlyOpenedPathsList'")
            row = cursor.fetchone()
            if row:
                data = json.loads(row[0])
                entries = data.get('entries', [])
                for entry in entries:
                    uri = entry.get('folderUri') or entry.get('fileUri')
                    if uri:
                        parsed = urlparse(uri)
                        path = ""
                        if parsed.scheme == 'file':
                            path = unquote(parsed.path)
                        else:
                            path = uri
                        
                        if path and path not in seen:
                            seen.add(path)
                            projects_list.append(path)
        except Exception as e:
            pass
        finally:
            if 'conn' in locals():
                conn.close()
                
    return projects_list

def fuzzy_match(query, text):
    """Simple fuzzy match: checks if query characters appear in text in order (case-insensitive)."""
    if not query:
        return True
    query = query.lower()
    text = text.lower()
    q_idx = 0
    for char in text:
        if q_idx < len(query) and char == query[q_idx]:
            q_idx += 1
    return q_idx == len(query)

def draw_menu(stdscr, selected_row_idx, projects, search_query="", pinned=set(), mode="insiders"):
    stdscr.clear()
    h, w = stdscr.getmaxyx()
    
    # Colors
    # Pair 1: Selected Item (Black on Cyan)
    # Pair 2: Header (Magenta)
    # Pair 3: Path (Blue)
    # Pair 4: Pinned (Yellow)
    # Pair 5: Mode Indicator (Green)
    
    # Title
    mode_label = MODES.get(mode, MODES["insiders"])["label"]
    title = f" Project Launcher [{mode_label}] "
    if w > len(title):
        stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
        stdscr.addstr(1, w//2 - len(title)//2, title)
        stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
    
    # Search Bar (if active)
    if search_query:
        search_text = f"Search: {search_query}"
        stdscr.addstr(2, 1, search_text, curses.A_BOLD)
        
    # List Area
    list_start_y = 3 if not search_query else 4
    max_display_items = h - list_start_y - 2 # Leave room for footer
    
    if max_display_items <= 0:
        stdscr.addstr(0,0, "Window too small")
        return

    # Scroll logic
    start_idx = 0
    if len(projects) > max_display_items:
        if selected_row_idx >= max_display_items // 2:
            start_idx = selected_row_idx - (max_display_items // 2)
            # Clamp to end
            if start_idx + max_display_items > len(projects):
                start_idx = len(projects) - max_display_items
        # Clamp to start
        if start_idx < 0: start_idx = 0
            
    end_idx = min(start_idx + max_display_items, len(projects))
    
    for i in range(start_idx, end_idx):
        project_path = projects[i]
        name = os.path.basename(project_path) or project_path
        is_pinned = project_path in pinned
        
        # Truncate path if too long
        pin_mark = "★ " if is_pinned else "  "
        display_str = f" {pin_mark}{name} "
        path_str = f"({project_path})"
        
        y = list_start_y + (i - start_idx)
        
        # Calculate available width
        # We want: [Name] [Path]
        # If selected: Highlight whole line
        
        if i == selected_row_idx:
            stdscr.attron(curses.color_pair(1))
            # Pad with spaces to fill width for background color effect
            line_content = f" > {pin_mark}{name}  {path_str}"
            if len(line_content) < w - 2:
                line_content += " " * (w - 2 - len(line_content))
            else:
                line_content = line_content[:w-2]
            stdscr.addstr(y, 1, line_content)
            stdscr.attroff(curses.color_pair(1))
        else:
            if is_pinned:
                stdscr.attron(curses.color_pair(4) | curses.A_BOLD)
                stdscr.addstr(y, 1, pin_mark)
                stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)
            
            stdscr.attron(curses.A_BOLD)
            stdscr.addstr(y, 3, name)
            stdscr.attroff(curses.A_BOLD)
            
            # Draw path in different color
            stdscr.attron(curses.color_pair(3))
            remaining_w = w - 4 - len(name) - 2
            if remaining_w > len(path_str):
                stdscr.addstr(y, 4 + len(name), path_str)
            elif remaining_w > 5:
                stdscr.addstr(y, 4 + len(name), path_str[:remaining_w-3] + "...")
            stdscr.attroff(curses.color_pair(3))

    # Footer
    if search_query:
        footer_text = " ENTER: Open | ESC: Clear Search | Type to filter "
    else:
        footer_text = " ENTER: Open | n: New | o: Open path | /: Search | p: Pin | x: Remove | t: Terminal | TAB: Switch | q: Quit "
        
    # Truncate footer if too long
    if len(footer_text) > w - 2:
        footer_text = footer_text[:w-5] + "..."
        
    stdscr.attron(curses.color_pair(2))
    stdscr.addstr(h-1, 1, footer_text)
    stdscr.attroff(curses.color_pair(2))
    
    stdscr.refresh()

def get_input(stdscr, y, prompt, default_text="", is_path=False):
    curses.curs_set(1)
    stdscr.attron(curses.color_pair(2))
    stdscr.addstr(y, 1, prompt)
    stdscr.attroff(curses.color_pair(2))
    
    # Input loop
    input_text = list(default_text)
    
    # Tab completion state
    tab_matches = []
    tab_index = -1
    last_key_was_tab = False
    
    while True:
        # Clear line after prompt
        stdscr.move(y, 1 + len(prompt))
        stdscr.clrtoeol()
        
        # Print current text
        stdscr.addstr(y, 1 + len(prompt), "".join(input_text))
        
        key = stdscr.getch()
        
        if key == 9 and is_path: # Tab
            if not last_key_was_tab:
                # New tab sequence, find matches
                current_str = "".join(input_text)
                expanded = os.path.expanduser(current_str)
                dirname, basename = os.path.split(expanded)
                
                # If input ends with separator, we are looking for content inside that dir
                if current_str.endswith(os.sep):
                    dirname = expanded
                    basename = ""
                
                search_dir = dirname if dirname else "."
                
                if os.path.isdir(search_dir):
                    try:
                        files = os.listdir(search_dir)
                        matches = []
                        for f in files:
                            if f.startswith(basename):
                                if os.path.isdir(os.path.join(search_dir, f)):
                                    matches.append(f)
                        matches.sort()
                        
                        if matches:
                            tab_matches = []
                            for m in matches:
                                if dirname:
                                    candidate = os.path.join(dirname, m)
                                else:
                                    candidate = m
                                
                                # Check if it's a dir to append separator
                                # User requested NOT to add trailing slash automatically
                                # if os.path.isdir(candidate):
                                #    candidate += os.sep
                                tab_matches.append(candidate)
                            
                            tab_index = 0
                            input_text = list(tab_matches[0])
                    except OSError:
                        tab_matches = []
            else:
                # Cycle through existing matches
                if tab_matches:
                    tab_index = (tab_index + 1) % len(tab_matches)
                    input_text = list(tab_matches[tab_index])
            
            last_key_was_tab = True
            continue
            
        else:
            # Reset tab state
            last_key_was_tab = False
            tab_matches = []
            tab_index = -1
            
            if key == 27: # ESC
                return None
            elif key in [curses.KEY_ENTER, 10, 13]:
                break
            elif key in [curses.KEY_BACKSPACE, 127, 8]:
                if input_text:
                    input_text.pop()
            elif 32 <= key <= 126:
                input_text.append(chr(key))
            
    curses.curs_set(0)
    return "".join(input_text).strip()

def remove_project(project_path):
    """Removes the project_path from all discovered state databases."""
    for db_path in ALL_DB_PATHS:
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM ItemTable WHERE key = 'history.recentlyOpenedPathsList'")
            row = cursor.fetchone()
            if row:
                data = json.loads(row[0])
                entries = data.get('entries', [])
                
                new_entries = []
                modified = False
                for entry in entries:
                    uri = entry.get('folderUri') or entry.get('fileUri')
                    if uri:
                        parsed = urlparse(uri)
                        path = ""
                        if parsed.scheme == 'file':
                            path = unquote(parsed.path)
                        else:
                            path = uri
                        
                        if path == project_path:
                            modified = True
                            continue # Skip this entry to remove it
                    
                    new_entries.append(entry)
                
                if modified:
                    data['entries'] = new_entries
                    new_json = json.dumps(data)
                    cursor.execute("UPDATE ItemTable SET value = ? WHERE key = 'history.recentlyOpenedPathsList'", (new_json,))
                    conn.commit()
        except Exception as e:
            pass
        finally:
            if 'conn' in locals():
                conn.close()

def main(stdscr):
    # Initialize colors
    curses.start_color()
    curses.use_default_colors()
    
    # Define pairs
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)
    curses.init_pair(2, curses.COLOR_MAGENTA, -1)
    curses.init_pair(3, curses.COLOR_BLUE, -1)
    curses.init_pair(4, curses.COLOR_YELLOW, -1) # Pinned
    
    curses.curs_set(0) # Hide cursor
    
    config = load_config()
    pinned = set(config.get("pinned", []))
    mode = config.get("mode", "insiders")
    
    # Validate mode
    if mode not in MODE_ORDER:
        mode = "insiders"
    
    def refresh_projects():
        raw_projects = get_projects(mode)
        valid_projects = list(raw_projects)
        # Add pinned projects if they are not in history (optional, but good for persistence)
        for p in pinned:
            if p not in valid_projects and os.path.exists(p):
                valid_projects.append(p)
        return valid_projects

    all_projects = refresh_projects()

    current_row = 0
    search_mode = False
    search_query = ""
    
    while True:
        # Sort projects: Pinned first, then others
        # We do this dynamically to handle pinning toggles
        sorted_projects = sorted(all_projects, key=lambda p: (0 if p in pinned else 1, p))
        
        # Filter by search
        if search_query:
            filtered_projects = [p for p in sorted_projects if fuzzy_match(search_query, p)]
        else:
            filtered_projects = sorted_projects

        # Ensure current_row is valid
        if filtered_projects:
            current_row = max(0, min(current_row, len(filtered_projects) - 1))
        else:
            current_row = 0
            
        draw_menu(stdscr, current_row, filtered_projects, search_query if search_mode else "", pinned, mode)
        key = stdscr.getch()
        
        if search_mode:
            if key in [curses.KEY_ENTER, 10, 13]:
                if filtered_projects:
                    selected = filtered_projects[current_row]
                    # Launch
                    bin_name = MODES.get(mode, MODES["insiders"])["cmd"]
                    subprocess.Popen([bin_name, selected], start_new_session=True)
                    return # Exit after launch? Or stay? Usually exit.
            elif key == 27: # ESC
                search_mode = False
                search_query = ""
            elif key in [curses.KEY_BACKSPACE, 127, 8]:
                if search_query:
                    search_query = search_query[:-1]
                    current_row = 0
            elif key in [curses.KEY_UP, curses.KEY_DOWN]:
                if key == curses.KEY_UP and current_row > 0:
                    current_row -= 1
                elif key == curses.KEY_DOWN and current_row < len(filtered_projects) - 1:
                    current_row += 1
            elif 32 <= key <= 126:
                search_query += chr(key)
                current_row = 0
        else:
            if key in [curses.KEY_UP, ord('k')] and current_row > 0:
                current_row -= 1
            elif key in [curses.KEY_DOWN, ord('j')] and current_row < len(filtered_projects) - 1:
                current_row += 1
            elif key == ord('q') or key == ord('Q'):
                break
            elif key == ord('x') or key == ord('X'):
                 if filtered_projects:
                    selected = filtered_projects[current_row]
                    # Remove from DBs
                    remove_project(selected)
                    # Remove from pinned if present
                    if selected in pinned:
                        pinned.remove(selected)
                        config["pinned"] = list(pinned)
                        save_config(config)
                    # Refresh list
                    all_projects = refresh_projects()
                    # current_row will be clamped in next loop iteration
            elif key == ord('/'):
                search_mode = True
                search_query = ""
            elif key == ord('p') or key == ord('P'):
                if filtered_projects:
                    selected = filtered_projects[current_row]
                    if selected in pinned:
                        pinned.remove(selected)
                    else:
                        pinned.add(selected)
                    config["pinned"] = list(pinned)
                    save_config(config)
            elif key == 9 or key == ord('s') or key == ord('S'): # TAB or s
                # Cycle mode
                try:
                    current_idx = MODE_ORDER.index(mode)
                    next_idx = (current_idx + 1) % len(MODE_ORDER)
                    mode = MODE_ORDER[next_idx]
                except ValueError:
                    mode = "insiders"
                    
                config["mode"] = mode
                save_config(config)
                all_projects = refresh_projects()
                current_row = 0
            elif key == ord('t') or key == ord('T'):
                if filtered_projects:
                    selected = filtered_projects[current_row]
                    # Try to detect terminal
                    # KDE: konsole
                    # Gnome: gnome-terminal
                    # Generic: x-terminal-emulator
                    terminals = ["konsole", "gnome-terminal", "xfce4-terminal", "x-terminal-emulator", "kitty", "alacritty"]
                    launched = False
                    for t in terminals:
                        if subprocess.call(["which", t], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
                            # Different terminals have different flags for working dir
                            if t == "gnome-terminal" or t == "xfce4-terminal":
                                subprocess.Popen([t, "--working-directory", selected], start_new_session=True)
                            elif t == "konsole":
                                subprocess.Popen([t, "--workdir", selected], start_new_session=True)
                            else:
                                # Fallback, might not open in correct dir for some
                                subprocess.Popen([t], cwd=selected, start_new_session=True)
                            launched = True
                            break
                    if not launched:
                        # Last resort: xdg-open (might open file manager)
                        subprocess.Popen(["xdg-open", selected], start_new_session=True)
                    
                    return # Exit after launch
            elif key == ord('n') or key == ord('N'):
                h, w = stdscr.getmaxyx()
                stdscr.move(h-3, 0); stdscr.clrtoeol()
                stdscr.move(h-2, 0); stdscr.clrtoeol()
                
                name = get_input(stdscr, h-3, "Project Name: ")
                if name:
                    default_loc = "/home/prashant/Documents/github/"
                    location = get_input(stdscr, h-2, "Location: ", default_loc, is_path=True)
                    
                    if location and not location.endswith(os.sep):
                        location += os.sep
                    
                    new_path = os.path.join(location, name)
                    if not os.path.exists(new_path):
                        try:
                            os.makedirs(new_path)
                            # Add to projects list immediately?
                            # It will be added on next run or if we refresh.
                            # Let's just return to open it.
                            bin_name = MODES.get(mode, MODES["insiders"])["cmd"]
                            subprocess.Popen([bin_name, new_path], start_new_session=True)
                            return
                        except OSError:
                            pass
                    else:
                        bin_name = MODES.get(mode, MODES["insiders"])["cmd"]
                        subprocess.Popen([bin_name, new_path], start_new_session=True)
                        return
            elif key == ord('o') or key == ord('O'):
                h, w = stdscr.getmaxyx()
                stdscr.move(h-2, 0); stdscr.clrtoeol()
                
                default_loc = "/home/prashant/Documents/github/"
                location = get_input(stdscr, h-2, "Open Path: ", default_loc, is_path=True)
                
                if location:
                    if os.path.exists(location):
                        bin_name = MODES.get(mode, MODES["insiders"])["cmd"]
                        subprocess.Popen([bin_name, location], start_new_session=True)
                        return
            elif key in [curses.KEY_ENTER, 10, 13]:
                if filtered_projects:
                    selected = filtered_projects[current_row]
                    bin_name = MODES.get(mode, MODES["insiders"])["cmd"]
                    subprocess.Popen([bin_name, selected], start_new_session=True)
                    return
            
    return None

if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except Exception as e:
        print(f"An error occurred: {e}")

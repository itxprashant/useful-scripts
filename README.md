# Useful Scripts

In this project, I store helpful scripts that help me in development, DevOps, and general productivity.

## Scripts

### VS Code Launcher (`vscode_launcher.py`)

A terminal-based UI (TUI) project launcher for Visual Studio Code and other IDEs. It reads your recently opened projects from VS Code's state database and allows you to quickly launch them.

**Features:**
- **Recent Projects:** Automatically lists projects from VS Code history.
- **Search:** Fuzzy search through your projects.
- **Unified History:** Aggregates recent projects from all installed IDEs (VS Code, Insiders, Cursor, Antigravity, etc.).
- **Dynamic IDE Support:** Automatically detects installed IDEs.
- **Pinning:** Pin frequently used projects to the top of the list.
- **Terminal Integration:** Quickly open a terminal in the selected project directory.
- **New Project:** Create new project directories directly from the launcher.

**Usage:**

Run the script directly from the terminal:

```bash
./vscode_launcher.py
```

**Controls:**
- `UP` / `DOWN` / `j` / `k`: Navigate the list
- `ENTER`: Open selected project
- `/`: Search
- `p`: Pin/Unpin selected project
- `t`: Open terminal in selected project
- `n`: Create a new project
- `o`: Open a specific path
- `TAB` / `s`: Cycle through discovered IDEs (VS Code, Cursor, etc.)
- `x`: Remove selected project from all databases

- `q`: Quit

**Requirements:**
- Python 3
- `curses` (usually included with Python on Linux)
- `sqlite3` module

## Installation

Clone the repository and ensure the scripts are executable:

```bash
git clone <repository-url>
cd scripts
chmod +x *.py
```

## Contributing

Feel free to add your own useful scripts to this collection!

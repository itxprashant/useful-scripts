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

### Codeforces Launcher (`codeforces_launcher.py`)

A two-mode helper for Codeforces practice. By default it opens your local Codeforces workspace in VS Code and `codeforces.com` in a new Chrome window. With `-p` it launches a TUI that lists your unsolved problems (per rating) and opens the chosen one in Chrome plus the workspace in VS Code.

**Features:**
- **Quick Launch:** One command to open both the workspace (`/home/prashant/Documents/github/codeforces` by default) in VS Code and Codeforces in a fresh Chrome window.
- **Unsolved Problems TUI:** Pulls all rated problems from the Codeforces API and removes any you've ever submitted with verdict `OK` for the configured handle (`prashantt492` by default).
- **Rating Filter:** Cycle through every rating bucket that still has unsolved problems.
- **One-Key Open:** Hit `Enter` on a problem to open it in a new Chrome window and launch the workspace in VS Code in the same step.
- **Stdlib Only:** Uses `urllib`, `curses`, and `argparse` — no extra dependencies.

**Usage:**

```bash
./codeforces_launcher.py        # open workspace + codeforces.com
./codeforces_launcher.py -p     # launch the unsolved-problems TUI
```

**TUI Controls:**
- `UP` / `DOWN` / `j` / `k`: Navigate problem list
- `TAB` / `Shift+TAB` / `←` / `→` / `h` / `l`: Switch rating bucket
- `PgUp` / `PgDn`, `g` / `G`: Jump
- `ENTER`: Open selected problem in Chrome and the workspace in VS Code
- `r`: Refetch problems and submissions
- `q` / `ESC`: Quit

**Requirements:**
- Python 3 (stdlib only)
- `code` (VS Code) in `PATH`
- One of: `google-chrome`, `google-chrome-stable`, `chromium`, `chromium-browser` in `PATH`
- Network access to `codeforces.com/api`

To use a different handle or workspace path, edit the constants at the top of `codeforces_launcher.py` (`CF_HANDLE`, `PROJECT_DIR`).

## Installation

Clone the repository and ensure the scripts are executable:

```bash
git clone <repository-url>
cd scripts
chmod +x *.py
```

## Contributing

Feel free to add your own useful scripts to this collection!

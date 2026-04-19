#!/usr/bin/env python3
"""Codeforces launcher.

Default: open the local Codeforces workspace in VS Code and codeforces.com in Chrome.
With --problems / -p: launch a curses TUI to browse unsolved problems for the
configured handle, filtered by rating, and open the chosen one in Chrome.
"""
import argparse
import curses
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

PROJECT_DIR = "/home/prashant/Documents/github/codeforces"
CODEFORCES_URL = "https://codeforces.com/"
EDITOR = "code"
CHROME_CANDIDATES = ["google-chrome-beta", "google-chrome", "google-chrome-stable", "chromium", "chromium-browser"]
CF_HANDLE = "prashantt492"
CF_API = "https://codeforces.com/api"


# --------------------------------------------------------------------------- #
# Process / browser helpers
# --------------------------------------------------------------------------- #
def spawn_detached(cmd):
    """Launch cmd fully detached so this script can exit immediately."""
    try:
        subprocess.Popen(
            cmd,
            start_new_session=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
        return True
    except OSError as exc:
        print(f"Failed to launch {cmd[0]}: {exc}", file=sys.stderr)
        return False


def find_chrome():
    for binary in CHROME_CANDIDATES:
        if shutil.which(binary):
            return binary
    return None


# --------------------------------------------------------------------------- #
# Codeforces API
# --------------------------------------------------------------------------- #
def _fetch_json(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "codeforces_launcher"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def fetch_problems_and_solved(handle):
    """Returns (problems_by_rating, total_unsolved)."""
    problemset = _fetch_json(f"{CF_API}/problemset.problems")
    if problemset.get("status") != "OK":
        raise RuntimeError(problemset.get("comment", "problemset.problems failed"))
    problems = problemset["result"]["problems"]

    status = _fetch_json(f"{CF_API}/user.status?handle={handle}")
    if status.get("status") != "OK":
        raise RuntimeError(status.get("comment", "user.status failed"))

    solved = set()
    for sub in status["result"]:
        if sub.get("verdict") == "OK":
            p = sub.get("problem", {})
            cid = p.get("contestId")
            idx = p.get("index")
            if cid is not None and idx is not None:
                solved.add((cid, idx))

    by_rating = {}
    for p in problems:
        if "rating" not in p or "contestId" not in p:
            continue
        if (p["contestId"], p["index"]) in solved:
            continue
        by_rating.setdefault(p["rating"], []).append(p)

    for rating in by_rating:
        by_rating[rating].sort(key=lambda x: (-x["contestId"], x["index"]))

    return by_rating


def problem_url(problem):
    return f"https://codeforces.com/problemset/problem/{problem['contestId']}/{problem['index']}"


# --------------------------------------------------------------------------- #
# TUI
# --------------------------------------------------------------------------- #
def _safe_addstr(stdscr, y, x, text, attr=0):
    h, w = stdscr.getmaxyx()
    if y < 0 or y >= h or x < 0 or x >= w:
        return
    text = text[: max(0, w - x - 1)]
    try:
        stdscr.addstr(y, x, text, attr)
    except curses.error:
        pass


def _draw(stdscr, by_rating, ratings, rating_idx, row, status_msg=""):
    stdscr.erase()
    h, w = stdscr.getmaxyx()

    title = f" Codeforces Unsolved — {CF_HANDLE} "
    _safe_addstr(stdscr, 0, max(0, (w - len(title)) // 2), title,
                 curses.color_pair(2) | curses.A_BOLD)

    # Rating filter row
    _safe_addstr(stdscr, 2, 1, "Rating:", curses.A_BOLD)
    x = 1 + len("Rating:") + 1
    for i, r in enumerate(ratings):
        label = f" {r} "
        if x + len(label) >= w - 1:
            _safe_addstr(stdscr, 2, x, "…")
            break
        if i == rating_idx:
            _safe_addstr(stdscr, 2, x, label, curses.color_pair(1))
        else:
            _safe_addstr(stdscr, 2, x, label, curses.color_pair(3))
        x += len(label) + 1

    items = by_rating.get(ratings[rating_idx], []) if ratings else []
    list_y = 4
    max_items = h - list_y - 2
    if max_items <= 0:
        _safe_addstr(stdscr, 0, 0, "Window too small")
        stdscr.refresh()
        return items

    count_str = f" {len(items)} unsolved at rating {ratings[rating_idx]} " if ratings else " 0 "
    _safe_addstr(stdscr, 3, 1, count_str, curses.color_pair(4))

    start = 0
    if len(items) > max_items:
        if row >= max_items // 2:
            start = row - max_items // 2
            if start + max_items > len(items):
                start = len(items) - max_items
        start = max(start, 0)
    end = min(start + max_items, len(items))

    for i in range(start, end):
        p = items[i]
        ident = f"{p['contestId']}{p['index']}"
        name = p.get("name", "")
        tags = ", ".join(p.get("tags", []))
        # Build a line that fits the window
        prefix = f"  {ident:<8} {name}"
        suffix = f"  [{tags}]" if tags else ""
        line = prefix + suffix
        if len(line) > w - 2:
            line = line[: w - 5] + "..."
        else:
            line = line + " " * (w - 2 - len(line))

        y = list_y + (i - start)
        if i == row:
            _safe_addstr(stdscr, y, 1, line, curses.color_pair(1))
        else:
            _safe_addstr(stdscr, y, 1, line)

    footer = status_msg or " Tab/←/→ rating  ↑/↓ move  Enter open  r refresh  q quit "
    _safe_addstr(stdscr, h - 1, 1, footer, curses.color_pair(2))

    stdscr.refresh()
    return items


def run_tui(stdscr):
    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)   # selection
    curses.init_pair(2, curses.COLOR_MAGENTA, -1)                # title / footer
    curses.init_pair(3, curses.COLOR_GREEN, -1)                  # ratings
    curses.init_pair(4, curses.COLOR_YELLOW, -1)                 # info

    chrome = find_chrome()

    def load():
        stdscr.erase()
        _safe_addstr(stdscr, 0, 0, f"Fetching problems and submissions for {CF_HANDLE}…",
                     curses.A_BOLD)
        stdscr.refresh()
        return fetch_problems_and_solved(CF_HANDLE)

    try:
        by_rating = load()
    except (urllib.error.URLError, RuntimeError, ValueError) as exc:
        stdscr.erase()
        _safe_addstr(stdscr, 0, 0, f"Failed to fetch: {exc}")
        _safe_addstr(stdscr, 2, 0, "Press any key to exit.")
        stdscr.getch()
        return

    ratings = sorted(by_rating.keys())
    if not ratings:
        stdscr.erase()
        _safe_addstr(stdscr, 0, 0, "No unsolved rated problems found. Nice!")
        _safe_addstr(stdscr, 2, 0, "Press any key to exit.")
        stdscr.getch()
        return

    rating_idx = 0
    row = 0
    status_msg = ""

    while True:
        items = _draw(stdscr, by_rating, ratings, rating_idx, row, status_msg)
        status_msg = ""
        key = stdscr.getch()

        if key in (ord("q"), ord("Q"), 27):
            return
        elif key in (curses.KEY_UP, ord("k")):
            if items and row > 0:
                row -= 1
        elif key in (curses.KEY_DOWN, ord("j")):
            if items and row < len(items) - 1:
                row += 1
        elif key in (curses.KEY_LEFT, ord("h"), curses.KEY_BTAB, 353):
            # Left arrow / h / Shift+Tab
            if rating_idx > 0:
                rating_idx -= 1
                row = 0
        elif key in (curses.KEY_RIGHT, ord("l"), 9):
            # Right arrow / l / Tab
            if rating_idx < len(ratings) - 1:
                rating_idx += 1
                row = 0
        elif key == curses.KEY_PPAGE:
            row = max(0, row - 10)
        elif key == curses.KEY_NPAGE:
            if items:
                row = min(len(items) - 1, row + 10)
        elif key in (curses.KEY_HOME, ord("g")):
            row = 0
        elif key in (curses.KEY_END, ord("G")):
            if items:
                row = len(items) - 1
        elif key in (curses.KEY_ENTER, 10, 13):
            if not items:
                continue
            url = problem_url(items[row])
            if chrome is None:
                status_msg = " Chrome not found in PATH. "
                continue
            spawn_detached([chrome, "--new-window", url])
            if shutil.which(EDITOR) and os.path.isdir(PROJECT_DIR):
                spawn_detached([EDITOR, PROJECT_DIR])
            return
        elif key in (ord("r"), ord("R")):
            try:
                by_rating = load()
                ratings = sorted(by_rating.keys())
                if not ratings:
                    status_msg = " No unsolved rated problems. "
                    continue
                if rating_idx >= len(ratings):
                    rating_idx = len(ratings) - 1
                row = 0
            except (urllib.error.URLError, RuntimeError, ValueError) as exc:
                status_msg = f" Refresh failed: {exc} "


# --------------------------------------------------------------------------- #
# Default action: open editor + codeforces.com
# --------------------------------------------------------------------------- #
def open_workspace_and_site():
    if not os.path.isdir(PROJECT_DIR):
        print(f"Project directory not found: {PROJECT_DIR}", file=sys.stderr)
        return 1

    if shutil.which(EDITOR) is None:
        print(f"Editor '{EDITOR}' not found in PATH.", file=sys.stderr)
        return 1

    chrome = find_chrome()
    if chrome is None:
        print("Chrome not found in PATH. Tried: " + ", ".join(CHROME_CANDIDATES),
              file=sys.stderr)
        return 1

    editor_ok = spawn_detached([EDITOR, PROJECT_DIR])
    browser_ok = spawn_detached([chrome, "--new-window", CODEFORCES_URL])

    if editor_ok:
        print(f"Opened {PROJECT_DIR} in {EDITOR}.")
    if browser_ok:
        print(f"Opened {CODEFORCES_URL} in {chrome}.")
    return 0 if (editor_ok and browser_ok) else 1


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "-p", "--problems",
        action="store_true",
        help="Launch TUI to pick an unsolved problem (filtered by rating).",
    )
    args = parser.parse_args()

    if args.problems:
        try:
            curses.wrapper(run_tui)
        except KeyboardInterrupt:
            pass
        return 0

    return open_workspace_and_site()


if __name__ == "__main__":
    sys.exit(main())

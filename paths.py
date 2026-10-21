"""Where the game reads and writes files.

Running from source (python main.py) both point at the project folder, so
nothing changes during development. In the PyInstaller .exe the game files
are unpacked inside the bundle, which may not be writable (e.g. Program
Files), so saves and settings go to %APPDATA%\\DinoPodds instead.
"""
import os
import sys

FROZEN = getattr(sys, 'frozen', False)

# Read-only game files (assets/, maps): main.py chdirs here so every
# relative 'assets/...' path keeps working.
BASE_DIR = sys._MEIPASS if FROZEN else os.path.dirname(os.path.abspath(__file__))

# Writable files: SAVES/ and settings.json.
if FROZEN:
    USER_DIR = os.path.join(os.environ.get('APPDATA') or os.path.expanduser('~'), 'DinoPodds')
    os.makedirs(USER_DIR, exist_ok=True)
else:
    USER_DIR = BASE_DIR

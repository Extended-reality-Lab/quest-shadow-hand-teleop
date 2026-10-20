#!/usr/bin/env bash
# macOS / Linux setup. Windows uses setup.ps1.
set -euo pipefail

if ! command -v python3.12 >/dev/null 2>&1; then
    echo "python3.12 not found. Install it with: brew install python@3.12" >&2
    exit 1
fi

python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

echo "Setup complete. Check: .venv/bin/python -c 'import mujoco; print(mujoco.__version__)'"
echo "On macOS, launch viewer scripts with: .venv/bin/mjpython <script>.py"

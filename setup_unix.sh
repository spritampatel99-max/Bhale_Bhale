#!/usr/bin/env bash
# NovaMart - one-time local setup for Linux/macOS (safe to re-run; never deletes your data).
set -e
cd "$(dirname "$0")"

PY="$(command -v python3 || command -v python || true)"
if [ -z "$PY" ]; then
  echo "[ERROR] Python 3.12+ was not found. Install it from https://www.python.org/downloads/ or your package manager." >&2
  exit 1
fi
if ! "$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)'; then
  echo "[ERROR] Django 6 needs Python 3.12 or newer. Found: $("$PY" --version)" >&2
  exit 1
fi

if [ ! -x venv/bin/python ]; then
  echo "[1/5] Creating virtual environment in ./venv ..."
  "$PY" -m venv venv || { echo "[ERROR] venv creation failed. On Debian/Ubuntu: sudo apt install python3-venv" >&2; exit 1; }
else
  echo "[1/5] Virtual environment already exists - reusing it."
fi

echo "[2/5] Installing dependencies ..."
venv/bin/python -m pip install --upgrade pip >/dev/null
venv/bin/python -m pip install -r requirements.txt

echo "[3/5] Applying database migrations ..."
venv/bin/python manage.py migrate

echo "[4/5] Loading demo data (safe to repeat; no duplicates) ..."
venv/bin/python manage.py seed_demo_data --with-demo-users

echo "[5/5] Running system check ..."
venv/bin/python manage.py check

echo
echo "Setup complete. Start the website with: ./run_unix.sh"

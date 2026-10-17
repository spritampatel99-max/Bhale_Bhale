#!/usr/bin/env bash
# NovaMart - start the development server (Linux/macOS).
set -e
cd "$(dirname "$0")"
if [ ! -x venv/bin/python ] || ! venv/bin/python -c 'import django' 2>/dev/null; then
  echo "[ERROR] Environment not ready. Run ./setup_unix.sh first." >&2
  exit 1
fi
if [ ! -f novamart.sqlite3 ]; then
  echo "Database not found - creating it and loading demo data ..."
  venv/bin/python manage.py migrate
  venv/bin/python manage.py seed_demo_data --with-demo-users
else
  venv/bin/python manage.py migrate --noinput >/dev/null
fi
echo
echo " Store:         http://127.0.0.1:8000/"
echo " Dashboard:     http://127.0.0.1:8000/dashboard/"
echo " Django admin:  http://127.0.0.1:8000/admin/"
echo " Press CTRL+C to stop."
echo
exec venv/bin/python manage.py runserver

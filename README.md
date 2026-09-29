# Sunday School Administration System

Single Django application: server-rendered templates, htmx for partial
updates, Alpine.js for small client-side interactivity, Tailwind CSS for
styling. No separate frontend project, no REST API, no JWT — Django's own
session-based login handles auth.

## Requirements

- Python 3.11+
- PostgreSQL (or SQLite for local development)
- The Tailwind CSS standalone CLI (no Node/npm needed — see below)

## Setup (Windows / PowerShell)

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env`:

- For local testing: set `DJANGO_DEBUG=1`, `DJANGO_HTTPS=0`,
  `DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1`, and leave every `DB_*` line
  blank — the app falls back to SQLite automatically when no database is
  configured.

```powershell
python manage.py migrate
python manage.py seed          # creates the first Head account and prints its password
python manage.py runserver
```

## Tailwind CSS (no npm required)

Download the standalone CLI for your OS from
https://github.com/tailwindlabs/tailwindcss/releases (e.g.
`tailwindcss-windows-x64.exe`), place it in the project root as
`tailwindcss.exe`, then run, in a second terminal, left running while you
work:

```powershell
.\tailwindcss.exe -i school/static/school/css/input.css -o school/static/school/css/app.css --watch
```

This watches `input.css` and every template for class names used, and
regenerates `app.css` automatically. Nothing else in the project needs a
build step.

## Project layout

See the architecture section of the SRS for the full folder-by-folder
breakdown and the reasoning behind it.

## Deployment

See `deploy/` for the VPS setup script, gunicorn service file, nginx config,
and backup script.

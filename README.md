# EduShare (Flask)

A simple educational resource sharing app built with **Python (Flask)**, **SQLite (SQL via SQLAlchemy)**, **JavaScript**, **HTML**, and **CSS**.

## Features
- User account creation & login (Flask-Login, password hashing).
- Upload educational resources (PDF, video, text, any file).
- Per‑account content management (folder-like explorer: create folders, move, delete).
- Search by title (name), author, and subject.
- Rank resources by reviews (1–10 stars), average rating displayed and sortable.

## Quick Start

```bash
# 1) Create a virtual environment (recommended)
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
# source .venv/bin/activate

# 2) Install dependencies
pip install -r requirements.txt

# 3) Set environment variables (development)
set FLASK_APP=app.py        # Windows (cmd)
# export FLASK_APP=app.py   # macOS/Linux

# 4) Initialize the database (first run only)
python app.py --initdb

# 5) Run
flask run --debug
```

The app will start at http://127.0.0.1:5000

## Default configuration
- SQLite database file at `instance/edushare.db` (auto-created).
- Upload directory: `uploads/`.

## Notes
- This is a teaching scaffold: concise, readable, and ready to extend.
- For production, configure `SECRET_KEY`, use a proper database, and serve static files behind a web server.
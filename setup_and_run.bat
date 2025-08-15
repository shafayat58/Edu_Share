@echo off
echo Setting up EduShare Flask project...

:: Create virtual environment
python -m venv venv
call venv\Scripts\activate

:: Install dependencies
pip install --upgrade pip
pip install Flask Flask-SQLAlchemy Flask-Login

:: Initialize database
python app.py --initdb

:: Set Flask environment variables
set FLASK_APP=app.py
set FLASK_DEBUG=1

:: Initialize Git
if not exist .git (
    git init
    git add .
    git commit -m "Initial commit of EduShare Flask app"
    echo Git repository initialized.
) else (
    echo Git already initialized.
)

:: Run Flask server
flask run --host=0.0.0.0 --port=5000

pause

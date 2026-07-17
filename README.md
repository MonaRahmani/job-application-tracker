# Job Application Tracker

A full-stack web application to help job seekers track their applications.

## Why I Built It

I built this project from a personal need during my job search to stay organized and keep track of application progress. It also demonstrates my full-stack development skills across backend APIs, database modeling, and frontend interaction.

## Tech Stack

- Python Flask
- SQLAlchemy
- SQLite
- HTML
- CSS
- JavaScript

## Features

- Add job applications
- View all applications
- Update existing applications
- Delete applications
- Filter applications by status
- Private user accounts with session-based authentication
- Resume profile uploads (PDF or TXT)
- Per-application resume/job-description match scores and suggestions

## How to Run

1. Install dependencies
2. Run backend server
3. Open the app in your browser

```bash
# 1) Install dependencies
cd backend
python3 -m pip install -r requirements.txt

# 2) Configure OpenAI and run the backend server
export OPENAI_API_KEY="your-api-key"
# Optional: export OPENAI_MATCH_MODEL="gpt-5.6-luna"
python3 app.py

# 3) Visit http://127.0.0.1:5000
```

Set a private `SECRET_KEY` environment variable before deploying. The local fallback
is intended for development only.

Resume matching uses OpenAI's Responses API. The API key is read only by the backend
from `OPENAI_API_KEY` and is never sent to the browser.

## Project Structure

```text
job-tracker/
├── README.md
├── backend/
│   ├── app.py
│   ├── database.py
│   ├── models.py
│   └── requirements.txt
└── frontend/
    ├── index.html
    ├── style.css
    └── app.js
```

## Future Improvements

- Authentication
- Deployment to cloud
- Email notifications

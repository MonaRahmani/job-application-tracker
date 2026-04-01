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

## How to Run

1. Install dependencies
2. Run backend server
3. Open frontend in browser

```bash
# 1) Install dependencies
cd backend
python3 -m pip install -r ../requirements.txt

# 2) Run backend server
python3 app.py

# 3) Open frontend in browser
# In a new terminal:
cd ../frontend
open index.html
```

## Project Structure

```text
job-tracker/
├── README.md
├── requirements.txt
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

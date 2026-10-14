# Job Application Tracker

A web application for tracking job applications, built for COP4751. It stores companies, jobs, applications, and contacts in MySQL, serves them through a Flask backend with HTML/CSS templates, and includes a Job Match page that ranks jobs by how many of your skills they require.

## Tech Stack

Python 3 with Flask, MySQL 8 (the `jobs.requirements` and `applications.interview_data` columns use the JSON type, so MySQL 5.7+ is required), and plain HTML/CSS served from Flask templates.

## Setup

1. Clone the repository and open the project folder.
2. Create and activate a virtual environment: `python3 -m venv venv && source venv/bin/activate` (on Windows: `venv\Scripts\activate`).
3. Install dependencies: `pip install -r requirements.txt`.
4. Create the database and load the sample data: `mysql -u root -p < schema.sql`. This drops and recreates the four tables, so it is safe to re-run for a clean reset.
5. Copy `config.example.py` to `config.py` and set your MySQL password. `config.py` is git-ignored and never committed.
6. Start the app: `python app.py`, then open http://127.0.0.1:5000.

## Project Structure

`app.py` holds the Flask routes, `database.py` holds the connection and query helpers (`get_db`, `fetch_all`, `fetch_one`, `execute`), `schema.sql` creates and seeds the database, `templates/` contains the Jinja pages that extend `base.html`, and `static/style.css` holds all styling.

## Features

The dashboard shows totals for each table, applications grouped by status, and the five most recent applications.

## Database

Four tables linked by foreign keys: `jobs` and `contacts` belong to a company, and `applications` belong to a job. Deleting a company cascades to its jobs, contacts, and their applications. `job_type` and `status` are ENUMs, and the two JSON columns hold a job's required skills and an application's interview rounds.

## Demo and Documentation

AI tool usage is documented in AI_USAGE.md

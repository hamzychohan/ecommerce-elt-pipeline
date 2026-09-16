import json
import os
import random
import subprocess
from datetime import datetime, timedelta

# Variables for configuration
START_DATE = "2023-08-01"  # Start date (format: YYYY-MM-DD)
END_DATE = "2023-11-08"    # End date (format: YYYY-MM-DD)
MAX_COMMITS_PER_DAY = 6    # Max commits per day
MIN_COMMITS_PER_DAY = 0    # Min commits per day
FILE_PATH = "./data.json"  # JSON file to store commit data
TXT_FILE_PATH = "./commit_dates.txt"  # Text file to store commit dates

# GitHub profile author details
GIT_USER_NAME = "Hamza Chohan"
GIT_USER_EMAIL = "hamzychohan@users.noreply.github.com"

# Generic commit messages according to the repository
COMMIT_MESSAGES = [
    "update project configuration and environment settings",
    "fix minor bug in API extraction pipeline",
    "refactor DuckDB loader schema and table initialization",
    "update dbt staging models and transformation logic",
    "code cleanup and formatting across pipeline modules",
    "feature: enhance raw data ingestion and JSON validation",
    "chore: update dependencies and requirements.txt",
    "fix typo in dbt mart revenue calculation model",
    "optimize DuckDB query performance for customer churn mart",
    "update test suites for FastAPI mock endpoints",
    "minor tweaks in analytics report generation script",
    "refactor helper utilities and S3 storage adapter wrapper",
    "integrate local file fallback for raw data ingestion",
    "update Dockerfile and docker-compose service definitions",
    "refactor Redshift warehouse loading schema and queries",
    "implement customer lifetime value semantic metric helper",
    "enhance pipeline orchestration and error logging",
    "update documentation and AWS deployment architecture guide"
]

# Convert start and end date to datetime objects
start_date = datetime.strptime(START_DATE, "%Y-%m-%d")
end_date = datetime.strptime(END_DATE, "%Y-%m-%d")

def make_commit(n):
    if n == 0:
        subprocess.run(["git", "push", "origin", "main", "--force"])
        return

    # Randomly decide how many commits to make on this day/iteration
    commits_today = random.randint(MIN_COMMITS_PER_DAY, MAX_COMMITS_PER_DAY)

    days_range = (end_date - start_date).days

    for _ in range(commits_today):
        random_days_offset = random.randint(0, days_range)
        random_seconds = random.randint(0, 86399)
        commit_datetime = start_date + timedelta(days=random_days_offset, seconds=random_seconds)

        date_str = commit_datetime.strftime("%Y-%m-%dT%H:%M:%S")
        msg = random.choice(COMMIT_MESSAGES)

        env = os.environ.copy()
        env["GIT_AUTHOR_NAME"] = GIT_USER_NAME
        env["GIT_COMMITTER_NAME"] = GIT_USER_NAME
        env["GIT_AUTHOR_EMAIL"] = GIT_USER_EMAIL
        env["GIT_COMMITTER_EMAIL"] = GIT_USER_EMAIL
        env["GIT_AUTHOR_DATE"] = date_str
        env["GIT_COMMITTER_DATE"] = date_str

        data = {"date": date_str}
        print(f"{date_str}: {msg}")

        # Write commit date to JSON file
        with open(FILE_PATH, "w") as f:
            json.dump(data, f)

        # Write commit date to text file
        with open(TXT_FILE_PATH, "a") as f_txt:
            f_txt.write(f"{date_str}: {msg}\n")

        # Add and commit to Git with explicit author & committer dates
        subprocess.run(["git", "add", FILE_PATH, TXT_FILE_PATH], env=env)
        subprocess.run(["git", "commit", "--date", date_str, "-m", msg], env=env)

    make_commit(n - 1)

# Start making commits
make_commit(90)
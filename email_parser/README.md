# Synthesis Tracker

Extract and analyze activity data from Synthesis Tutor emails.

## Features

Parses two types of emails:
- **Weekly Progress Reports**: Daily Active Minutes breakdown, games played, lessons
- **Daily Session Reports**: Day, time, duration, and session topics

## Setup

1. Install dependencies:
```bash
python3 -m venv venv
source venv/bin/activate
pip install beautifulsoup4
```

2. Configure email access in `config.py`:
```python
IMAP_SERVER = "mail.kazer.org"
USERNAME = "your_email@domain.com"
PASSWORD = "your_password"
```

## Usage

Run the tracker:
```bash
python3 synthesis_tracker.py
```

## Output

Results are saved to `synthesis_data.json` containing:
- Session details (day, time, duration, topic)
- Weekly progress (daily minutes breakdown)
- Summary statistics

Example output:
```
Session Emails: 20 sessions, 650 minutes total (32.5 min average)
Weekly Progress: 12 weeks, 1152 minutes total (96 min/week average)
```
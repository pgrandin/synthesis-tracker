# Email Parser Component

Searches and retrieves progress emails and session emails from Synthesis Tutor.

## Features
- Connects to IMAP server
- Searches for emails from `no-reply@tutor.synthesis.com`
- Parses two types of emails:
  - **Weekly Progress Reports**: "Zoey's progress with Synthesis Tutor"
    - Daily Active Minutes table (7-day breakdown)
    - Games played with durations
    - Lessons in progress
  - **Daily Session Reports**: "Zoey's Synthesis Session: [Topic]"
    - Day, time, and duration (e.g., "Saturday, 4:44pm - 37.8 minutes")
    - Session topic and summary
    - Activities completed
- Batch fetching to handle large mailboxes efficiently

## Configuration
Edit `config.py` with your IMAP settings:
- `IMAP_SERVER`: Your IMAP server hostname
- `USERNAME`: Email username
- `PASSWORD`: Email password

## Usage
```bash
python3 email_search.py
```

## Found Emails
The script identifies weekly progress reports and displays:
- Email ID
- Subject
- From address
- Date received
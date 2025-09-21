# Email Parser Component

Searches and retrieves progress emails from Synthesis Tutor.

## Features
- Connects to IMAP server
- Searches for emails from `no-reply@tutor.synthesis.com`
- Filters for "Zoey's progress with Synthesis Tutor" subject
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
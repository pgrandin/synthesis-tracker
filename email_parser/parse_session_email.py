#!/usr/bin/env python3
"""
Parse daily session emails to extract session details
"""

from bs4 import BeautifulSoup
import re
from datetime import datetime
import json


def parse_session_details(html_content):
    """Extract session details from HTML email"""
    soup = BeautifulSoup(html_content, 'html.parser')

    session_data = {}

    # Try to extract from HTML structure
    # Look for the pattern: "MONDAY, 3:38PM - 33.1 MINUTES"
    for p in soup.find_all('p'):
        text = p.get_text(strip=True).upper()

        # Pattern: DAY, TIME - DURATION MINUTES
        match = re.match(r'(\w+),\s*(\d{1,2}:\d{2}[AP]M)\s*-\s*([\d.]+)\s*MINUTES', text)
        if match:
            session_data['day'] = match.group(1).capitalize()
            session_data['time'] = match.group(2).lower()
            session_data['duration_minutes'] = float(match.group(3))
            break

    # Also try plain text pattern
    if not session_data:
        text = soup.get_text()
        match = re.search(r'(\w+DAY),\s*(\d{1,2}:\d{2}[APap][Mm])\s*[-–]\s*([\d.]+)\s*[Mm]inutes', text, re.IGNORECASE)
        if match:
            session_data['day'] = match.group(1).capitalize()
            session_data['time'] = match.group(2).lower()
            session_data['duration_minutes'] = float(match.group(3))

    return session_data


def parse_session_text(text_content):
    """Extract session details from plain text email"""
    session_data = {}

    # Pattern: DAY, TIME - DURATION MINUTES
    match = re.search(r'(\w+DAY),\s*(\d{1,2}:\d{2}[APap][Mm])\s*[-–]\s*([\d.]+)\s*[Mm][Ii][Nn][Uu][Tt][Ee][Ss]', text_content, re.IGNORECASE)
    if match:
        session_data['day'] = match.group(1).capitalize()
        session_data['time'] = match.group(2).lower()
        session_data['duration_minutes'] = float(match.group(3))

    return session_data


def extract_session_summary(text_content):
    """Extract the session summary text"""
    lines = text_content.split('\n')

    # Find the line with session details
    session_line_idx = -1
    for i, line in enumerate(lines):
        if re.search(r'\d+\.\d+\s*MINUTES', line, re.IGNORECASE):
            session_line_idx = i
            break

    # Extract summary (usually follows the session details)
    summary = ""
    if session_line_idx >= 0 and session_line_idx < len(lines) - 1:
        # Get text after the session line
        summary_lines = []
        for line in lines[session_line_idx + 1:]:
            line = line.strip()
            if line and not line.startswith('—') and not line.startswith('Login'):
                summary_lines.append(line)
            elif line.startswith('Login') or line.startswith('View in'):
                break
        summary = ' '.join(summary_lines)

    return summary.strip()


def parse_session_email(html_content=None, text_content=None, email_date=None, subject=None):
    """Parse complete session email and return structured data"""
    result = {
        'date': email_date,
        'subject': subject,
        'session': {}
    }

    # Extract session topic from subject
    if subject and "Zoey's Synthesis Session:" in subject:
        topic = subject.split("Zoey's Synthesis Session:")[1].strip()
        result['session_topic'] = topic

    # Try HTML parsing first
    if html_content:
        session_data = parse_session_details(html_content)
        if session_data:
            result['session'].update(session_data)

    # Fall back to text parsing
    if not result['session'] and text_content:
        session_data = parse_session_text(text_content)
        if session_data:
            result['session'].update(session_data)

    # Extract summary
    if text_content:
        summary = extract_session_summary(text_content)
        if summary:
            result['summary'] = summary

    return result


def main():
    """Test the parser with sample session emails"""
    import sys

    # Use the most recent session email file
    email_file = 'email_11630.html' if len(sys.argv) < 2 else sys.argv[1]
    text_file = email_file.replace('.html', '.txt')

    try:
        html_content = None
        text_content = None

        # Read HTML file
        try:
            with open(email_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
        except FileNotFoundError:
            print(f"HTML file {email_file} not found")

        # Read text file
        try:
            with open(text_file, 'r', encoding='utf-8') as f:
                text_content = f.read()
        except FileNotFoundError:
            print(f"Text file {text_file} not found")

        if not html_content and not text_content:
            print("No email content found. Run fetch_email_content.py first.")
            return

        # Parse the email
        result = parse_session_email(
            html_content=html_content,
            text_content=text_content,
            email_date='Mon, 11 Aug 2025 23:05:11 +0000',
            subject="Zoey's Synthesis Session: Fraction Fun and Triumph!"
        )

        # Print results
        print(json.dumps(result, indent=2))

        # Summary
        print("\n" + "="*50)
        print("SESSION SUMMARY")
        print("="*50)
        if result.get('session_topic'):
            print(f"Topic: {result['session_topic']}")
        if result.get('session'):
            session = result['session']
            print(f"Day: {session.get('day', 'Unknown')}")
            print(f"Time: {session.get('time', 'Unknown')}")
            print(f"Duration: {session.get('duration_minutes', 0)} minutes")
        if result.get('summary'):
            print(f"\nSummary: {result['summary'][:200]}...")

    except Exception as e:
        print(f"Error parsing email: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
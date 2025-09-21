#!/usr/bin/env python3
"""
Process all session and progress emails for comprehensive analysis
"""

import imaplib
import email
from email.header import decode_header
import socket
import json
from datetime import datetime
from parse_progress_email import parse_progress_email
from parse_session_email import parse_session_email
try:
    import config
except ImportError:
    print("Error: config.py not found")
    import sys
    sys.exit(1)

# Set timeout for connections
socket.setdefaulttimeout(30)


def connect_to_imap(server, username, password):
    """Connect to IMAP server and login"""
    try:
        print(f"Connecting to {server}:993 with SSL...")
        imap = imaplib.IMAP4_SSL(server, 993)
        print(f"Logging in as {username}...")
        imap.login(username, password)
        print(f"Successfully connected to {server}")
        return imap
    except Exception as e:
        print(f"Error connecting to server: {e}")
        return None


def fetch_and_parse_email(imap, email_id, email_type='session'):
    """Fetch and parse a single email"""
    try:
        # Fetch the email
        result, msg_data = imap.fetch(str(email_id), "(RFC822)")

        if result != 'OK':
            return None

        # Parse email
        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)

        # Get metadata
        email_date = msg['Date']
        subject = decode_header(msg["Subject"])[0][0]
        if isinstance(subject, bytes):
            subject = subject.decode()

        # Extract body
        body_html = None
        body_text = None

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/html" and not body_html:
                    body_html = part.get_payload(decode=True)
                    if body_html:
                        body_html = body_html.decode('utf-8', errors='ignore')
                elif content_type == "text/plain" and not body_text:
                    body_text = part.get_payload(decode=True)
                    if body_text:
                        body_text = body_text.decode('utf-8', errors='ignore')
        else:
            # Single part message
            content_type = msg.get_content_type()
            payload = msg.get_payload(decode=True)
            if payload:
                if content_type == "text/html":
                    body_html = payload.decode('utf-8', errors='ignore')
                else:
                    body_text = payload.decode('utf-8', errors='ignore')

        # Parse based on type
        if email_type == 'session':
            parsed_data = parse_session_email(
                html_content=body_html,
                text_content=body_text,
                email_date=email_date,
                subject=subject
            )
        else:  # progress
            parsed_data = parse_progress_email(body_html, email_date)

        parsed_data['email_id'] = email_id
        return parsed_data

    except Exception as e:
        print(f"Error parsing email {email_id}: {e}")

    return None


def find_all_synthesis_emails(imap):
    """Find all Synthesis emails (both session and progress)"""
    try:
        # Select inbox
        print("Selecting INBOX...")
        result, data = imap.select("INBOX")
        total_msgs = int(data[0].decode())
        print(f"INBOX selected: {result}, contains {total_msgs} messages")

        sender = "no-reply@tutor.synthesis.com"

        # Get the last 2000 messages
        start_uid = max(1, total_msgs - 2000)
        end_uid = total_msgs

        print(f"Searching messages {start_uid} to {end_uid}...")
        session_ids = []
        progress_ids = []

        # Fetch in batches
        batch_size = 50
        for batch_start in range(start_uid, end_uid + 1, batch_size):
            batch_end = min(batch_start + batch_size - 1, end_uid)

            try:
                # Fetch headers
                result, data = imap.fetch(f"{batch_start}:{batch_end}", "(BODY[HEADER.FIELDS (FROM SUBJECT)])")

                if result == 'OK' and data:
                    for i in range(0, len(data), 2):
                        if data[i] and isinstance(data[i], tuple) and len(data[i]) > 1:
                            raw_headers = data[i][1]
                            headers = email.message_from_bytes(raw_headers)

                            from_addr = headers.get("From", "")
                            if sender not in from_addr.lower():
                                continue

                            subject_header = headers.get("Subject", "")
                            if not subject_header:
                                continue

                            decoded = decode_header(subject_header)
                            subject = decoded[0][0]
                            if isinstance(subject, bytes):
                                subject = subject.decode()

                            msg_num = batch_start + (i // 2)

                            # Categorize
                            if "Zoey's Synthesis Session:" in subject:
                                session_ids.append(msg_num)
                            elif "Zoey's progress with Synthesis Tutor" in subject:
                                progress_ids.append(msg_num)

            except Exception as e:
                print(f"    Batch {batch_start}-{batch_end} failed: {e}")
                continue

        return session_ids, progress_ids

    except Exception as e:
        print(f"Error searching emails: {e}")
        return [], []


def main():
    """Process all Synthesis emails"""

    # Connect to IMAP server
    imap = connect_to_imap(config.IMAP_SERVER, config.USERNAME, config.PASSWORD)
    if not imap:
        return

    try:
        # Find all emails
        print("\nSearching for Synthesis emails...")
        session_ids, progress_ids = find_all_synthesis_emails(imap)

        print(f"\nFound {len(session_ids)} session emails")
        print(f"Found {len(progress_ids)} progress emails")

        all_sessions = []
        all_progress = []

        # Process session emails
        if session_ids:
            print("\nProcessing session emails...")
            for idx, email_id in enumerate(session_ids[:10], 1):  # Limit to 10 for testing
                print(f"  Processing session {idx}/{min(10, len(session_ids))} (ID: {email_id})...")
                parsed = fetch_and_parse_email(imap, email_id, 'session')
                if parsed and parsed.get('session'):
                    all_sessions.append(parsed)
                    print(f"    ✓ {parsed['session'].get('day', '')} - {parsed['session'].get('duration_minutes', 0)} min")

        # Process progress emails
        if progress_ids:
            print("\nProcessing progress emails...")
            for idx, email_id in enumerate(progress_ids, 1):
                print(f"  Processing progress {idx}/{len(progress_ids)} (ID: {email_id})...")
                parsed = fetch_and_parse_email(imap, email_id, 'progress')
                if parsed:
                    all_progress.append(parsed)
                    print(f"    ✓ Total weekly: {parsed.get('total_weekly_minutes', 0)} min")

        # Save data
        if all_sessions:
            with open('session_data.json', 'w') as f:
                json.dump(all_sessions, f, indent=2)
            print(f"\n✓ Saved {len(all_sessions)} session records")

        if all_progress:
            with open('progress_data_updated.json', 'w') as f:
                json.dump(all_progress, f, indent=2)
            print(f"✓ Saved {len(all_progress)} progress records")

        # Combined summary
        print("\n" + "="*60)
        print("COMBINED ACTIVITY SUMMARY")
        print("="*60)

        # Session summary
        if all_sessions:
            total_session_minutes = sum(s['session'].get('duration_minutes', 0) for s in all_sessions)
            avg_session = total_session_minutes / len(all_sessions) if all_sessions else 0
            print(f"\nSession Emails:")
            print(f"  Total sessions: {len(all_sessions)}")
            print(f"  Total time: {total_session_minutes:.1f} minutes")
            print(f"  Average per session: {avg_session:.1f} minutes")

            # Show recent sessions
            print("\n  Recent Sessions:")
            for session in sorted(all_sessions, key=lambda x: x.get('email_id', 0), reverse=True)[:5]:
                s = session['session']
                topic = session.get('session_topic', 'Unknown')[:40]
                print(f"    - {s.get('day', 'Unknown')} {s.get('time', '')}: {s.get('duration_minutes', 0)} min - {topic}...")

        # Progress summary
        if all_progress:
            total_weekly_minutes = sum(p.get('total_weekly_minutes', 0) for p in all_progress)
            avg_weekly = total_weekly_minutes / len(all_progress) if all_progress else 0
            print(f"\nWeekly Progress Emails:")
            print(f"  Total weeks: {len(all_progress)}")
            print(f"  Total time: {total_weekly_minutes} minutes")
            print(f"  Average per week: {avg_weekly:.1f} minutes")

    finally:
        # Logout
        try:
            imap.close()
            imap.logout()
            print("\nDisconnected from server")
        except:
            pass


if __name__ == "__main__":
    main()
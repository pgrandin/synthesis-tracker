#!/usr/bin/env python3
"""
Find daily session emails from Synthesis Tutor
"""

import imaplib
import email
from email.header import decode_header
import socket
import json
from datetime import datetime
try:
    import config
except ImportError:
    print("Error: config.py not found")
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


def find_session_emails(imap):
    """Find all daily session emails"""
    try:
        # Select inbox
        print("Selecting INBOX...")
        result, data = imap.select("INBOX")
        total_msgs = int(data[0].decode())
        print(f"INBOX selected: {result}, contains {total_msgs} messages")

        sender = "no-reply@tutor.synthesis.com"

        # Get the last 2000 messages to search
        start_uid = max(1, total_msgs - 2000)
        end_uid = total_msgs

        print(f"Searching messages {start_uid} to {end_uid}...")
        session_emails = []
        progress_emails = []

        # Fetch in batches
        batch_size = 50
        for batch_start in range(start_uid, end_uid + 1, batch_size):
            batch_end = min(batch_start + batch_size - 1, end_uid)
            print(f"  Checking batch {batch_start}-{batch_end}...")

            try:
                # Fetch headers for this batch
                result, data = imap.fetch(f"{batch_start}:{batch_end}", "(BODY[HEADER.FIELDS (FROM SUBJECT DATE)])")

                if result == 'OK' and data:
                    # Parse the fetched data
                    for i in range(0, len(data), 2):
                        if data[i] and isinstance(data[i], tuple) and len(data[i]) > 1:
                            raw_headers = data[i][1]
                            headers = email.message_from_bytes(raw_headers)

                            # Check sender
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
                            date = headers.get("Date", "")

                            # Categorize email
                            if "Zoey's Synthesis Session:" in subject:
                                session_emails.append({
                                    'id': msg_num,
                                    'subject': subject,
                                    'date': date
                                })
                                print(f"      Found session email: {subject[:50]}...")
                            elif "Zoey's progress with Synthesis Tutor" in subject:
                                progress_emails.append({
                                    'id': msg_num,
                                    'subject': subject,
                                    'date': date
                                })
                                print(f"      Found progress email")

            except Exception as e:
                print(f"    Batch failed: {e}")
                continue

        return session_emails, progress_emails

    except Exception as e:
        print(f"Error searching emails: {e}")
        return [], []


def main():
    """Main function to find all session emails"""

    # Connect to IMAP server
    imap = connect_to_imap(config.IMAP_SERVER, config.USERNAME, config.PASSWORD)
    if not imap:
        return

    try:
        # Find all session and progress emails
        print("\nSearching for Synthesis emails...")
        session_emails, progress_emails = find_session_emails(imap)

        print(f"\nFound {len(session_emails)} session emails")
        print(f"Found {len(progress_emails)} weekly progress emails")

        # Show recent session emails
        if session_emails:
            print("\n" + "="*60)
            print("RECENT SESSION EMAILS (last 10)")
            print("="*60)

            for email_info in sorted(session_emails, key=lambda x: x['id'], reverse=True)[:10]:
                print(f"\nID: {email_info['id']}")
                print(f"Subject: {email_info['subject']}")
                print(f"Date: {email_info['date']}")

            # Save to JSON for reference
            with open('session_emails_list.json', 'w') as f:
                json.dump(session_emails, f, indent=2)
            print(f"\n✓ Saved full list to session_emails_list.json")

            # Get the most recent one for analysis
            if session_emails:
                most_recent = sorted(session_emails, key=lambda x: x['id'], reverse=True)[0]
                print(f"\nMost recent session email ID: {most_recent['id']}")
                print(f"Use this ID to fetch: python3 fetch_email_content.py {most_recent['id']}")

    finally:
        # Logout and close connection
        try:
            imap.close()
            imap.logout()
            print("\nDisconnected from server")
        except:
            pass


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Process all progress emails and save extracted data
"""

import imaplib
import email
from email.header import decode_header
import socket
import json
from datetime import datetime
from parse_progress_email import parse_progress_email
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


def fetch_and_parse_email(imap, email_id):
    """Fetch and parse a single email"""
    try:
        # Fetch the email
        result, msg_data = imap.fetch(str(email_id), "(RFC822)")

        if result != 'OK':
            return None

        # Parse email
        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)

        # Get date
        email_date = msg['Date']

        # Extract body
        body_html = None

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/html":
                    body_html = part.get_payload(decode=True)
                    if body_html:
                        body_html = body_html.decode('utf-8', errors='ignore')
                        break
        else:
            # Single part message
            content_type = msg.get_content_type()
            if content_type == "text/html":
                payload = msg.get_payload(decode=True)
                if payload:
                    body_html = payload.decode('utf-8', errors='ignore')

        if body_html:
            # Parse the HTML content
            parsed_data = parse_progress_email(body_html, email_date)
            parsed_data['email_id'] = email_id
            return parsed_data

    except Exception as e:
        print(f"Error parsing email {email_id}: {e}")

    return None


def find_progress_emails(imap):
    """Find all progress emails"""
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
        matching_email_ids = []

        # Fetch in batches
        batch_size = 50
        for batch_start in range(start_uid, end_uid + 1, batch_size):
            batch_end = min(batch_start + batch_size - 1, end_uid)
            print(f"  Checking batch {batch_start}-{batch_end}...")

            try:
                # Fetch headers for this batch
                result, data = imap.fetch(f"{batch_start}:{batch_end}", "(BODY[HEADER.FIELDS (FROM SUBJECT)])")

                if result == 'OK' and data:
                    # Parse the fetched data
                    for i in range(0, len(data), 2):
                        if data[i] and isinstance(data[i], tuple) and len(data[i]) > 1:
                            raw_headers = data[i][1]
                            headers = email.message_from_bytes(raw_headers)

                            # Check sender and subject
                            from_addr = headers.get("From", "")
                            subject_header = headers.get("Subject", "")

                            if sender in from_addr.lower() and subject_header:
                                decoded = decode_header(subject_header)
                                subject = decoded[0][0]
                                if isinstance(subject, bytes):
                                    subject = subject.decode()

                                # Check for progress email
                                if "Zoey's progress with Synthesis Tutor" in subject:
                                    msg_num = batch_start + (i // 2)
                                    matching_email_ids.append(msg_num)
                                    print(f"      Found progress email ID: {msg_num}")

            except Exception as e:
                print(f"    Batch failed: {e}")
                continue

        return matching_email_ids

    except Exception as e:
        print(f"Error searching emails: {e}")
        return []


def main():
    """Main function to process all progress emails"""

    # Connect to IMAP server
    imap = connect_to_imap(config.IMAP_SERVER, config.USERNAME, config.PASSWORD)
    if not imap:
        return

    try:
        # Find all progress emails
        print("\nSearching for progress emails...")
        email_ids = find_progress_emails(imap)

        print(f"\nFound {len(email_ids)} progress emails")

        if email_ids:
            all_data = []

            # Process each email
            for idx, email_id in enumerate(email_ids, 1):
                print(f"\nProcessing email {idx}/{len(email_ids)} (ID: {email_id})...")
                parsed_data = fetch_and_parse_email(imap, email_id)

                if parsed_data:
                    all_data.append(parsed_data)
                    print(f"  ✓ Parsed successfully")
                    print(f"    Date: {parsed_data['date']}")
                    print(f"    Total Minutes: {parsed_data['total_weekly_minutes']}")
                else:
                    print(f"  ✗ Failed to parse")

            # Save all data to JSON
            if all_data:
                output_file = 'progress_data.json'
                with open(output_file, 'w') as f:
                    json.dump(all_data, f, indent=2)
                print(f"\n✓ Saved {len(all_data)} records to {output_file}")

                # Generate summary
                print("\n" + "="*60)
                print("SUMMARY OF ALL PROGRESS EMAILS")
                print("="*60)

                total_minutes = sum(d['total_weekly_minutes'] for d in all_data)
                avg_minutes = total_minutes / len(all_data) if all_data else 0

                print(f"Total Emails: {len(all_data)}")
                print(f"Total Minutes Across All Weeks: {total_minutes}")
                print(f"Average Weekly Minutes: {avg_minutes:.1f}")

                # Show trend
                print("\nWeekly Minutes Trend:")
                for data in sorted(all_data, key=lambda x: x['date']):
                    date_str = data['date'][:16] if data['date'] else 'Unknown'
                    bar = '█' * int(data['total_weekly_minutes'] / 5)
                    print(f"  {date_str}: {bar} {data['total_weekly_minutes']} min")

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
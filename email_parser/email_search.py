#!/usr/bin/env python3
"""
Search for emails from Synthesis Tutor about Zoey's progress
"""

import imaplib
import email
from email.header import decode_header
from datetime import datetime
import getpass
import sys
import socket
try:
    import config
except ImportError:
    config = None

# Set timeout for connections
socket.setdefaulttimeout(30)


def connect_to_imap(server, username, password, port=993, use_ssl=True):
    """Connect to IMAP server and login"""
    try:
        # Connect to the server
        if use_ssl:
            print(f"Connecting to {server}:{port} with SSL...")
            imap = imaplib.IMAP4_SSL(server, port)
        else:
            print(f"Connecting to {server}:{port} without SSL...")
            imap = imaplib.IMAP4(server, port)

        # Login
        print(f"Logging in as {username}...")
        imap.login(username, password)

        print(f"Successfully connected to {server}")
        return imap
    except Exception as e:
        print(f"Error connecting to server: {e}")
        return None


def search_synthesis_emails(imap):
    """Search for emails from Synthesis Tutor about Zoey's progress"""
    try:
        # Select inbox
        print("Selecting INBOX...")
        result, data = imap.select("INBOX")
        total_msgs = int(data[0].decode())
        print(f"INBOX selected: {result}, contains {total_msgs} messages")

        sender = "no-reply@tutor.synthesis.com"

        # Try getting UIDs of recent messages instead
        print(f"Getting UIDs of recent messages...")

        # Get the UID of the last 1000 messages
        start_uid = max(1, total_msgs - 1000)
        end_uid = total_msgs

        # Use UID FETCH for a range
        print(f"Fetching messages {start_uid} to {end_uid}...")
        matching_emails = []

        # Fetch in smaller batches to avoid timeout
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

                            # Get and decode subject
                            subject_header = headers.get("Subject", "")
                            if subject_header:
                                decoded = decode_header(subject_header)
                                subject = decoded[0][0]
                                if isinstance(subject, bytes):
                                    subject = subject.decode()
                            else:
                                continue

                            # Check for Synthesis emails
                            if sender in from_addr.lower():
                                print(f"      Found Synthesis email: {subject[:50]}...")

                                # Check exact match
                                if "Zoey's progress with Synthesis Tutor" in subject:
                                    msg_num = batch_start + (i // 2)
                                    matching_emails.append({
                                        'id': str(msg_num),
                                        'subject': subject,
                                        'from': from_addr,
                                        'date': headers.get("Date", "")
                                    })
                                    print(f"      ✓ MATCH FOUND!")

            except Exception as e:
                print(f"    Batch failed: {e}")
                continue

        return matching_emails

    except Exception as e:
        print(f"Error searching emails: {e}")
        return []


def display_results(emails):
    """Display found emails"""
    if not emails:
        print("\nNo matching emails found.")
        return

    print(f"\nFound {len(emails)} matching emails:")
    print("-" * 80)

    for idx, email_info in enumerate(emails, 1):
        print(f"{idx}. Email ID: {email_info['id']}")
        print(f"   Subject: {email_info['subject']}")
        print(f"   From: {email_info['from']}")
        print(f"   Date: {email_info['date']}")
        print("-" * 80)


def main():
    """Main function to run the email search"""
    print("Email Search for Synthesis Tutor Progress Reports")
    print("=" * 50)

    # Try to use config file first
    if config:
        server = config.IMAP_SERVER
        username = config.USERNAME
        password = config.PASSWORD
        print(f"Using configuration from config.py")
        print(f"Server: {server}")
        print(f"Username: {username}")
    else:
        # Get IMAP server details manually
        server = input("Enter IMAP server (e.g., imap.gmail.com): ").strip()
        if not server:
            print("Server is required")
            return

        username = input("Enter email username: ").strip()
        if not username:
            print("Username is required")
            return

        # Get password securely
        password = getpass.getpass("Enter email password: ")
        if not password:
            print("Password is required")
            return

    # Connect to IMAP server
    imap = connect_to_imap(server, username, password)
    if not imap:
        return

    try:
        # Search for emails
        print("\nSearching for emails...")
        matching_emails = search_synthesis_emails(imap)

        # Display results
        display_results(matching_emails)

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
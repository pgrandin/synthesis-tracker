#!/usr/bin/env python3
"""
Fetch full content of a specific email to analyze structure
"""

import imaplib
import email
from email.header import decode_header
import sys
import socket
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


def fetch_email_content(imap, email_id):
    """Fetch full content of a specific email"""
    try:
        # Select inbox
        result, data = imap.select("INBOX")
        if result != 'OK':
            print("Failed to select INBOX")
            return None

        # Fetch the email
        print(f"Fetching email ID {email_id}...")
        result, msg_data = imap.fetch(str(email_id), "(RFC822)")

        if result != 'OK':
            print("Failed to fetch email")
            return None

        # Parse email
        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)

        # Get basic info
        subject = decode_header(msg["Subject"])[0][0]
        if isinstance(subject, bytes):
            subject = subject.decode()

        print(f"\nSubject: {subject}")
        print(f"From: {msg['From']}")
        print(f"Date: {msg['Date']}")
        print("-" * 80)

        # Extract body
        body_html = None
        body_text = None

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()

                if content_type == "text/html":
                    body_html = part.get_payload(decode=True)
                    if body_html:
                        body_html = body_html.decode('utf-8', errors='ignore')
                elif content_type == "text/plain":
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

        return {
            'subject': subject,
            'from': msg['From'],
            'date': msg['Date'],
            'html': body_html,
            'text': body_text
        }

    except Exception as e:
        print(f"Error fetching email: {e}")
        return None


def save_content(email_data, email_id):
    """Save email content to files for analysis"""
    if email_data['html']:
        filename = f"email_{email_id}.html"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(email_data['html'])
        print(f"HTML content saved to {filename}")

    if email_data['text']:
        filename = f"email_{email_id}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(email_data['text'])
        print(f"Text content saved to {filename}")


def main():
    """Main function to fetch a specific email"""
    if len(sys.argv) > 1:
        email_id = sys.argv[1]
    else:
        # Use the most recent email found (12115)
        email_id = "12115"

    print(f"Fetching email with ID: {email_id}")

    # Connect to IMAP server
    imap = connect_to_imap(config.IMAP_SERVER, config.USERNAME, config.PASSWORD)
    if not imap:
        return

    try:
        # Fetch email content
        email_data = fetch_email_content(imap, email_id)

        if email_data:
            # Save to files
            save_content(email_data, email_id)

            # Show preview of text content
            if email_data['text']:
                print("\nText preview (first 500 chars):")
                print(email_data['text'][:500])

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
#!/usr/bin/env python3
"""
Synthesis Tracker - Extract activity data from Synthesis Tutor emails
"""

import imaplib
import email
from email.header import decode_header
import socket
import json
import re
from datetime import datetime
from bs4 import BeautifulSoup
import sys
import argparse

# Set timeout for connections
socket.setdefaulttimeout(30)


class SynthesisTracker:
    def __init__(self, server, username, password):
        self.server = server
        self.username = username
        self.password = password
        self.imap = None

    def connect(self):
        """Connect to IMAP server"""
        try:
            print(f"Connecting to {self.server}...")
            self.imap = imaplib.IMAP4_SSL(self.server, 993)
            self.imap.login(self.username, self.password)
            print("✓ Connected successfully")
            return True
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            return False

    def disconnect(self):
        """Disconnect from IMAP server"""
        if self.imap:
            try:
                self.imap.close()
                self.imap.logout()
                print("Disconnected from server")
            except:
                pass

    def search_emails(self, limit=2000):
        """Find all Synthesis emails"""
        try:
            result, data = self.imap.select("INBOX")
            total_msgs = int(data[0].decode())
            print(f"Searching {min(limit, total_msgs)} recent messages...")

            start_uid = max(1, total_msgs - limit)
            end_uid = total_msgs

            session_emails = []
            progress_emails = []

            # Batch fetch headers
            batch_size = 50
            for batch_start in range(start_uid, end_uid + 1, batch_size):
                batch_end = min(batch_start + batch_size - 1, end_uid)

                try:
                    result, data = self.imap.fetch(
                        f"{batch_start}:{batch_end}",
                        "(BODY[HEADER.FIELDS (FROM SUBJECT DATE)])"
                    )

                    if result == 'OK' and data:
                        for i in range(0, len(data), 2):
                            if data[i] and isinstance(data[i], tuple) and len(data[i]) > 1:
                                headers = email.message_from_bytes(data[i][1])

                                from_addr = headers.get("From", "")
                                if "no-reply@tutor.synthesis.com" not in from_addr.lower():
                                    continue

                                subject = self._decode_header(headers.get("Subject", ""))
                                msg_id = batch_start + (i // 2)
                                date = headers.get("Date", "")

                                if "Zoey's Synthesis Session:" in subject:
                                    session_emails.append({
                                        'id': msg_id, 'subject': subject, 'date': date
                                    })
                                elif "Zoey's progress with Synthesis Tutor" in subject:
                                    progress_emails.append({
                                        'id': msg_id, 'subject': subject, 'date': date
                                    })
                except Exception as e:
                    continue

            print(f"Found {len(session_emails)} session emails")
            print(f"Found {len(progress_emails)} weekly progress emails")
            return session_emails, progress_emails

        except Exception as e:
            print(f"Error searching: {e}")
            return [], []

    def fetch_email(self, email_id):
        """Fetch full email content"""
        try:
            result, msg_data = self.imap.fetch(str(email_id), "(RFC822)")
            if result != 'OK':
                return None

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            # Extract content and metadata
            content = {
                'html': None,
                'text': None,
                'date': msg.get('Date', ''),
                'subject': self._decode_header(msg.get('Subject', ''))
            }

            if msg.is_multipart():
                for part in msg.walk():
                    ct = part.get_content_type()
                    payload = part.get_payload(decode=True)
                    if payload:
                        try:
                            decoded = payload.decode('utf-8', errors='ignore')
                            if ct == "text/html":
                                content['html'] = decoded
                            elif ct == "text/plain":
                                content['text'] = decoded
                        except:
                            continue
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    content['text'] = payload.decode('utf-8', errors='ignore')

            return content
        except Exception as e:
            print(f"Error fetching email {email_id}: {e}")
            return None

    def parse_session(self, content, subject, date):
        """Parse session email"""
        data = {'subject': subject, 'date': date, 'type': 'session'}

        # Extract session topic
        if "Zoey's Synthesis Session:" in subject:
            data['topic'] = subject.split("Zoey's Synthesis Session:")[1].strip()

        # Parse session details from text
        text = content.get('text', '')
        match = re.search(
            r'(\w+DAY),\s*(\d{1,2}:\d{2}[APap][Mm])\s*[-–]\s*([\d.]+)\s*[Mm][Ii][Nn][Uu][Tt][Ee][Ss]',
            text, re.IGNORECASE
        )
        if match:
            data['day'] = match.group(1).capitalize()
            data['time'] = match.group(2).lower()
            data['duration_minutes'] = float(match.group(3))

        return data

    def parse_progress(self, content, subject, date):
        """Parse weekly progress email"""
        data = {'subject': subject, 'date': date, 'type': 'progress'}

        if not content.get('html'):
            return data

        soup = BeautifulSoup(content['html'], 'html.parser')

        # Parse Daily Active Minutes
        daily_minutes = {}
        days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

        minutes_divs = []
        for div in soup.find_all('div', style=lambda x: x and 'color:rgb(156,163,175)' in x):
            text = div.get_text(strip=True)
            if text.isdigit() or text == '':
                minutes_divs.append(int(text) if text else 0)

        if len(minutes_divs) >= 7:
            for i, day in enumerate(days):
                daily_minutes[day] = minutes_divs[i]
            data['daily_minutes'] = daily_minutes
            data['total_weekly_minutes'] = sum(daily_minutes.values())

        return data

    def process_all(self, save_to_file=True):
        """Process all emails and return/save results"""
        if not self.connect():
            return None

        try:
            sessions, progress = self.search_emails()

            results = {
                'sessions': [],
                'progress': [],
                'summary': {},
                'last_updated': datetime.now().isoformat()
            }

            # Process all session emails
            print("\nProcessing session emails...")
            for email_info in sessions:
                content = self.fetch_email(email_info['id'])
                if content:
                    # Use the actual email date from the fetched content
                    parsed = self.parse_session(
                        content,
                        content.get('subject', email_info['subject']),
                        content.get('date', email_info['date'])
                    )
                    parsed['email_id'] = email_info['id']
                    results['sessions'].append(parsed)

                    duration = parsed.get('duration_minutes', 0)
                    if duration:
                        print(f"  ✓ {parsed.get('day', '?')} - {duration:.1f} min")

            # Process weekly progress
            print("\nProcessing weekly progress emails...")
            for email_info in progress:
                content = self.fetch_email(email_info['id'])
                if content:
                    # Use the actual email date from the fetched content
                    parsed = self.parse_progress(
                        content,
                        content.get('subject', email_info['subject']),
                        content.get('date', email_info['date'])
                    )
                    parsed['email_id'] = email_info['id']
                    results['progress'].append(parsed)

                    total = parsed.get('total_weekly_minutes', 0)
                    print(f"  ✓ Week total: {total} min")

            # Calculate summary
            if results['sessions']:
                total_session_min = sum(
                    s.get('duration_minutes', 0) for s in results['sessions']
                )
                results['summary']['total_session_minutes'] = total_session_min
                results['summary']['avg_session_minutes'] = total_session_min / len(results['sessions'])
                results['summary']['session_count'] = len(results['sessions'])

            if results['progress']:
                total_weekly_min = sum(
                    p.get('total_weekly_minutes', 0) for p in results['progress']
                )
                results['summary']['total_weekly_minutes'] = total_weekly_min
                results['summary']['avg_weekly_minutes'] = total_weekly_min / len(results['progress'])
                results['summary']['week_count'] = len(results['progress'])

                # Calculate rolling averages
                sorted_progress = sorted(results['progress'], key=lambda x: x.get('date', ''), reverse=True)

                # Last 4 weeks average
                last_4_weeks = sorted_progress[:4]
                if last_4_weeks:
                    last_4_weeks_minutes = sum(p.get('total_weekly_minutes', 0) for p in last_4_weeks)
                    results['summary']['last_4_weeks_avg'] = last_4_weeks_minutes / len(last_4_weeks)
                else:
                    results['summary']['last_4_weeks_avg'] = 0

                # Last 7 days calculation (from most recent week's daily data)
                if sorted_progress and sorted_progress[0].get('daily_minutes'):
                    daily_data = sorted_progress[0]['daily_minutes']
                    last_7_days_total = sum(daily_data.values())
                    results['summary']['last_7_days_total'] = last_7_days_total
                    results['summary']['last_7_days_avg'] = last_7_days_total / 7
                else:
                    results['summary']['last_7_days_total'] = 0
                    results['summary']['last_7_days_avg'] = 0

                # Projection for current month (realistic target based on historical data)
                # Target: 60 min/week (~8.5 min/day), Stretch: 80 min/week (~11.5 min/day)
                target_weekly = 60  # Realistic target based on recent practice patterns
                stretch_weekly = 80  # Stretch goal for good weeks
                results['summary']['target_weekly_minutes'] = target_weekly
                results['summary']['stretch_weekly_minutes'] = stretch_weekly
                results['summary']['target_monthly_minutes'] = target_weekly * 4
                results['summary']['current_pace_vs_target'] = (results['summary'].get('last_4_weeks_avg', 0) / target_weekly * 100) if target_weekly > 0 else 0
                results['summary']['current_pace_vs_stretch'] = (results['summary'].get('last_4_weeks_avg', 0) / stretch_weekly * 100) if stretch_weekly > 0 else 0

            # Save to file
            if save_to_file:
                with open('synthesis_data.json', 'w') as f:
                    json.dump(results, f, indent=2)
                print(f"\n✓ Saved to synthesis_data.json")

                # Generate Home Assistant metrics file
                self.generate_ha_metrics(results)

            # Print summary
            self.print_summary(results)

            return results

        finally:
            self.disconnect()

    def generate_ha_metrics(self, results):
        """Generate Home Assistant compatible metrics file"""
        from datetime import datetime, timedelta

        # Calculate daily averages from the most recent weeks of data
        progress_data = results.get('progress', [])

        # Sort by date (most recent first)
        sorted_progress = sorted(progress_data, key=lambda x: x.get('email_id', 0), reverse=True)

        # Calculate 4-week daily average
        total_4week = 0
        days_4week = 0
        for week in sorted_progress[:4]:
            daily_minutes = week.get('daily_minutes', {})
            for day, minutes in daily_minutes.items():
                if minutes > 0:
                    total_4week += minutes
                    days_4week += 1

        avg_daily_4weeks = round(total_4week / days_4week, 1) if days_4week > 0 else 0

        # Calculate 2-week daily average
        total_2week = 0
        days_2week = 0
        for week in sorted_progress[:2]:
            daily_minutes = week.get('daily_minutes', {})
            for day, minutes in daily_minutes.items():
                if minutes > 0:
                    total_2week += minutes
                    days_2week += 1

        avg_daily_2weeks = round(total_2week / days_2week, 1) if days_2week > 0 else 0

        # Get latest session
        latest_session = None
        if results.get('sessions'):
            latest = results['sessions'][0]
            latest_session = {
                'topic': latest.get('topic', 'Unknown'),
                'duration_minutes': latest.get('duration_minutes', 0),
                'day': latest.get('day', 'Unknown'),
                'time': latest.get('time', 'Unknown'),
                'date': latest.get('date', '')
            }

        summary = results.get('summary', {})

        # Create HA metrics
        ha_metrics = {
            'average_daily_minutes_4weeks': avg_daily_4weeks,
            'average_daily_minutes_2weeks': avg_daily_2weeks,
            'total_sessions': summary.get('session_count', 0),
            'total_minutes': summary.get('total_session_minutes', 0),
            'average_session_minutes': round(summary.get('avg_session_minutes', 0), 1),
            'last_7_days_total': summary.get('last_7_days_total', 0),
            'last_7_days_average': round(summary.get('last_7_days_avg', 0), 1),
            'last_4_weeks_average_weekly': round(summary.get('last_4_weeks_avg', 0), 1),
            'last_2_weeks_average_weekly': round(sum(week.get('total_weekly_minutes', 0) for week in sorted_progress[:2]) / 2, 1) if len(sorted_progress) >= 2 else 0,
            'current_pace_vs_target': round(summary.get('current_pace_vs_target', 0), 1),
            'latest_session': latest_session,
            'last_updated': datetime.now().isoformat()
        }

        # Save HA metrics file
        with open('ha_metrics.json', 'w') as f:
            json.dump(ha_metrics, f, indent=2)

        print(f"✓ Saved ha_metrics.json")
        print(f"  - 4-week daily average: {ha_metrics['average_daily_minutes_4weeks']} minutes")
        print(f"  - 2-week daily average: {ha_metrics['average_daily_minutes_2weeks']} minutes")

    def print_summary(self, results):
        """Print activity summary"""
        print("\n" + "="*60)
        print("SYNTHESIS TRACKER SUMMARY")
        print("="*60)

        summary = results.get('summary', {})

        if summary.get('session_count'):
            print(f"\nSession Emails:")
            print(f"  Total: {summary['session_count']} sessions")
            print(f"  Total time: {summary['total_session_minutes']:.1f} minutes")
            print(f"  Average: {summary['avg_session_minutes']:.1f} min/session")

        if summary.get('week_count'):
            print(f"\nWeekly Progress:")
            print(f"  Total: {summary['week_count']} weeks")
            print(f"  Total time: {summary['total_weekly_minutes']} minutes")
            print(f"  Average: {summary['avg_weekly_minutes']:.1f} min/week")

        # Show recent activity
        if results['progress']:
            print("\nRecent Weekly Activity:")
            for prog in sorted(results['progress'], key=lambda x: x['email_id'], reverse=True)[:3]:
                daily = prog.get('daily_minutes', {})
                total = prog.get('total_weekly_minutes', 0)
                active_days = sum(1 for v in daily.values() if v > 0)
                print(f"  • {total} min across {active_days} days")

    def _decode_header(self, header):
        """Decode email header"""
        if not header:
            return ""
        decoded = decode_header(header)
        return decoded[0][0].decode() if isinstance(decoded[0][0], bytes) else decoded[0][0]


def main():
    parser = argparse.ArgumentParser(description='Track Synthesis Tutor activity')
    parser.add_argument('--server', default='mail.kazer.org', help='IMAP server')
    parser.add_argument('--user', default='pierre@kazer.org', help='Email username')
    parser.add_argument('--password', default='mHrH9gsF', help='Email password')
    parser.add_argument('--config', help='Config file (alternative to command line)')

    args = parser.parse_args()

    # Try to load config file if specified or exists
    if args.config:
        import importlib.util
        spec = importlib.util.spec_from_file_location("config", args.config)
        config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config)
        server = config.IMAP_SERVER
        username = config.USERNAME
        password = config.PASSWORD
    else:
        try:
            import config
            server = config.IMAP_SERVER
            username = config.USERNAME
            password = config.PASSWORD
        except ImportError:
            server = args.server
            username = args.user
            password = args.password

    # Run tracker
    tracker = SynthesisTracker(server, username, password)
    tracker.process_all()


if __name__ == "__main__":
    main()
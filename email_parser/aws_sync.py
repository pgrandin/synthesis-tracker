#!/usr/bin/env python3
"""
Sync Synthesis data to AWS S3
Uploads JSON data to S3 for dashboard consumption
"""

import json
import boto3
from datetime import datetime
import os
import sys
from pathlib import Path

# AWS Configuration
BUCKET_NAME = "synthesis-tracker-data"
REGION = "us-east-1"

def setup_aws_credentials():
    """Load AWS credentials from ~/.aws/pierre"""
    creds_file = Path.home() / ".aws" / "pierre"
    if creds_file.exists():
        with open(creds_file, 'r') as f:
            for line in f:
                if line.startswith('export AWS_ACCESS_KEY_ID='):
                    os.environ['AWS_ACCESS_KEY_ID'] = line.split('=')[1].strip()
                elif line.startswith('export AWS_SECRET_ACCESS_KEY='):
                    os.environ['AWS_SECRET_ACCESS_KEY'] = line.split('=')[1].strip()
        return True
    return False

def create_bucket_if_needed(s3_client):
    """Create S3 bucket if it doesn't exist"""
    try:
        s3_client.head_bucket(Bucket=BUCKET_NAME)
        print(f"✓ Bucket {BUCKET_NAME} exists")
    except:
        try:
            if REGION == 'us-east-1':
                s3_client.create_bucket(Bucket=BUCKET_NAME)
            else:
                s3_client.create_bucket(
                    Bucket=BUCKET_NAME,
                    CreateBucketConfiguration={'LocationConstraint': REGION}
                )
            print(f"✓ Created bucket {BUCKET_NAME}")

            # Enable versioning for data safety
            s3_client.put_bucket_versioning(
                Bucket=BUCKET_NAME,
                VersioningConfiguration={'Status': 'Enabled'}
            )
            print("✓ Enabled versioning")

            # Set bucket policy for public read (for dashboard)
            # Comment this out if you want private access only
            """
            policy = {
                "Version": "2012-10-17",
                "Statement": [{
                    "Sid": "PublicReadGetObject",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": ["s3:GetObject"],
                    "Resource": f"arn:aws:s3:::{BUCKET_NAME}/*"
                }]
            }
            s3_client.put_bucket_policy(
                Bucket=BUCKET_NAME,
                Policy=json.dumps(policy)
            )
            print("✓ Set public read policy")
            """

        except Exception as e:
            print(f"✗ Error creating bucket: {e}")
            return False
    return True

def upload_to_s3(s3_client, data):
    """Upload data to S3"""
    try:
        # Add metadata
        data['last_updated'] = datetime.now().isoformat()
        data['version'] = '1.0'

        # Upload main data file
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key='synthesis_data.json',
            Body=json.dumps(data, indent=2),
            ContentType='application/json',
            Metadata={
                'updated': datetime.now().isoformat(),
                'records': str(len(data.get('sessions', [])) + len(data.get('progress', [])))
            }
        )
        print(f"✓ Uploaded synthesis_data.json to s3://{BUCKET_NAME}/")

        # Also upload a latest.json for easy access
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key='latest.json',
            Body=json.dumps({
                'last_updated': data['last_updated'],
                'summary': data.get('summary', {}),
                'recent_activity': {
                    'sessions': len(data.get('sessions', [])),
                    'weeks': len(data.get('progress', [])),
                    'last_week_minutes': data.get('progress', [{}])[-1].get('total_weekly_minutes', 0) if data.get('progress') else 0
                }
            }, indent=2),
            ContentType='application/json'
        )
        print(f"✓ Uploaded latest.json summary")

        # Generate and upload a simple HTML viewer
        html_content = generate_html_viewer(data)
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key='index.html',
            Body=html_content,
            ContentType='text/html'
        )
        print(f"✓ Uploaded HTML viewer")

        return True

    except Exception as e:
        print(f"✗ Error uploading: {e}")
        return False

def generate_html_viewer(data):
    """Generate a simple HTML viewer for the data"""
    summary = data.get('summary', {})
    last_updated = data.get('last_updated', 'Unknown')

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Synthesis Tracker Data</title>
    <style>
        body {{ font-family: -apple-system, system-ui, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; }}
        .metric {{ display: inline-block; margin: 20px; padding: 20px; background: #f5f5f5; border-radius: 8px; }}
        .metric .value {{ font-size: 2em; font-weight: bold; color: #2563eb; }}
        .metric .label {{ color: #666; margin-top: 5px; }}
        h1 {{ color: #1e293b; }}
        .updated {{ color: #94a3b8; font-size: 0.9em; }}
        .download {{ margin-top: 30px; }}
        a {{ color: #2563eb; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <h1>🧠 Synthesis Tracker Data</h1>
    <p class="updated">Last updated: {last_updated}</p>

    <div class="metrics">
        <div class="metric">
            <div class="value">{summary.get('week_count', 0)}</div>
            <div class="label">Weeks Tracked</div>
        </div>
        <div class="metric">
            <div class="value">{summary.get('avg_weekly_minutes', 0):.0f}</div>
            <div class="label">Avg Minutes/Week</div>
        </div>
        <div class="metric">
            <div class="value">{summary.get('session_count', 0)}</div>
            <div class="label">Total Sessions</div>
        </div>
        <div class="metric">
            <div class="value">{summary.get('avg_session_minutes', 0):.0f}</div>
            <div class="label">Avg Minutes/Session</div>
        </div>
    </div>

    <div class="download">
        <h3>📥 Download Data</h3>
        <p>
            <a href="synthesis_data.json">Full Dataset (JSON)</a> |
            <a href="latest.json">Summary (JSON)</a>
        </p>
    </div>

    <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #e2e8f0;">
        <p style="color: #94a3b8; font-size: 0.85em;">
            Data is automatically synced from email reports.
            S3 Bucket: {BUCKET_NAME}
        </p>
    </div>
</body>
</html>"""

    return html

def get_s3_url():
    """Get the S3 URL for accessing data"""
    return f"https://{BUCKET_NAME}.s3.{REGION}.amazonaws.com/"

def main():
    """Main sync function"""
    print("🚀 AWS S3 Sync for Synthesis Tracker")
    print("=" * 50)

    # Setup credentials
    if not setup_aws_credentials():
        print("✗ Could not load AWS credentials from ~/.aws/pierre")
        return 1

    print("✓ AWS credentials loaded")

    # Load local data
    data_file = Path(__file__).parent / "synthesis_data.json"
    if not data_file.exists():
        print(f"✗ No data file found at {data_file}")
        print("  Run synthesis_tracker.py first to generate data")
        return 1

    with open(data_file, 'r') as f:
        data = json.load(f)

    print(f"✓ Loaded {len(data.get('sessions', []))} sessions, {len(data.get('progress', []))} weekly reports")

    # Initialize S3 client
    try:
        s3_client = boto3.client('s3', region_name=REGION)
        print("✓ Connected to AWS S3")
    except Exception as e:
        print(f"✗ Failed to connect to AWS: {e}")
        return 1

    # Create bucket if needed
    if not create_bucket_if_needed(s3_client):
        return 1

    # Upload data
    if upload_to_s3(s3_client, data):
        url = get_s3_url()
        print("\n" + "=" * 50)
        print("✅ Successfully synced to S3!")
        print(f"\n📊 Access your data at:")
        print(f"   JSON: {url}synthesis_data.json")
        print(f"   HTML: {url}index.html")
        print(f"   Summary: {url}latest.json")
        return 0

    return 1

if __name__ == "__main__":
    sys.exit(main())
#!/bin/bash
# Automated update and sync to S3
# Add to cron for daily updates: 0 18 * * * /path/to/update_and_sync.sh

cd /home/pierre/dev/pgrandin/synthesis/synthesis-tracker

# Activate virtual environment
source email_parser/venv/bin/activate

# Fetch latest emails and update local data
echo "Fetching latest emails..."
python3 email_parser/synthesis_tracker.py

# Sync to S3
echo "Syncing to S3..."
python3 email_parser/aws_sync.py

echo "Update complete!"
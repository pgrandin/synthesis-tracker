# AWS S3 Storage for Synthesis Tracker

## Setup Complete ✅

Your Synthesis data is now stored in AWS S3:
- **Bucket**: `synthesis-tracker-data`
- **Region**: `us-east-1`
- **Versioning**: Enabled (keeps history of changes)

## Access Your Data

### Via AWS CLI
```bash
source ~/.aws/pierre
aws s3 ls s3://synthesis-tracker-data/
aws s3 cp s3://synthesis-tracker-data/synthesis_data.json .
```

### Via Python/Dashboard
```python
import boto3
import json

s3 = boto3.client('s3')
response = s3.get_object(Bucket='synthesis-tracker-data', Key='synthesis_data.json')
data = json.loads(response['Body'].read())
```

## Files in S3

1. **synthesis_data.json** - Complete dataset (11KB)
   - All sessions and weekly reports
   - Updated timestamps
   - Summary statistics

2. **latest.json** - Quick summary (345 bytes)
   - Last update time
   - Recent activity summary
   - Perfect for status checks

3. **index.html** - Simple web viewer
   - Shows current statistics
   - Links to download JSON

## Automatic Updates

### Manual Update
```bash
./update_and_sync.sh
```

### Scheduled Updates (Cron)
Add to crontab for daily updates at 6pm:
```bash
crontab -e
# Add this line:
0 18 * * * /home/pierre/dev/pgrandin/synthesis/synthesis-tracker/update_and_sync.sh
```

## Cost Analysis

**Monthly Cost: < $0.001**
- Storage: 11KB × $0.023/GB = $0.0000003
- Requests: ~100/month × $0.0004/1000 = $0.00004
- **Annual Total: ~$0.01**

At this scale, you'll pay less than 1 cent per year.

## Security

- Bucket is **private** by default
- Access requires AWS credentials
- Versioning enabled for data recovery
- Can be made public if needed for external dashboards

## Dashboard Integration

Your dashboard can now:
1. Poll S3 a few times daily (minimal cost)
2. Cache data locally
3. Show historical trends with versioning

Example dashboard fetch:
```python
def fetch_from_s3():
    s3 = boto3.client('s3')
    obj = s3.get_object(Bucket='synthesis-tracker-data', Key='latest.json')
    return json.loads(obj['Body'].read())
```
import json
import uuid
import random
import time
import argparse
from datetime import datetime, timedelta
import boto3

# Configuration
NUM_NORMAL_LOGS = 100
NUM_ANOMALIES = 5

def generate_ip():
    return f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}"

def generate_log_entry(user_name, ip_address, country, timestamp, action="ConsoleLogin"):
    return {
        "eventVersion": "1.08",
        "userIdentity": {
            "type": "IAMUser",
            "principalId": str(uuid.uuid4())[:10],
            "arn": f"arn:aws:iam::123456789012:user/{user_name}",
            "accountId": "123456789012",
            "userName": user_name
        },
        "eventTime": timestamp.strftime('%Y-%m-%dT%H:%M:%SZ'),
        "eventSource": "signin.amazonaws.com",
        "eventName": action,
        "sourceIPAddress": ip_address,
        "country": country,
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)...",
        "requestParameters": None,
        "responseElements": {"ConsoleLogin": "Success"},
        "eventID": str(uuid.uuid4())
    }

def generate_all_logs():
    logs = []
    users = ["alice", "bob", "charlie", "dave"]
    countries = ["US", "UK", "CA", "JP", "DE"]

    # Generate normal logs
    base_time = datetime.utcnow() - timedelta(days=1)
    for _ in range(NUM_NORMAL_LOGS):
        user = random.choice(users)
        country = random.choice(countries)
        ip = generate_ip()
        timestamp = base_time + timedelta(minutes=random.randint(1, 1440))
        logs.append(generate_log_entry(user, ip, country, timestamp))

    # Generate "Impossible Travel" anomalies
    # Anomaly: Alice logs in from US, then 5 minutes later from RU
    for i in range(NUM_ANOMALIES):
        user = "alice_anomaly" + str(i)
        
        login1_time = base_time + timedelta(hours=i)
        login1 = generate_log_entry(user, "203.0.113.1", "US", login1_time)
        
        # 5 minutes later, login from Russia (impossible travel)
        login2_time = login1_time + timedelta(minutes=5)
        login2 = generate_log_entry(user, "198.51.100.1", "RU", login2_time)
        
        logs.append(login1)
        logs.append(login2)

    # Sort logs by time
    logs.sort(key=lambda x: x['eventTime'])
    return logs

def send_to_firehose(logs, stream_name):
    print(f"Streaming logs to Kinesis Firehose Delivery Stream: {stream_name}...")
    client = boto3.client('firehose')
    
    # Send records in batches to avoid hitting API limits
    batch_size = 500
    for i in range(0, len(logs), batch_size):
        batch = logs[i:i+batch_size]
        records = [{'Data': json.dumps(log) + '\n'} for log in batch]
        
        response = client.put_record_batch(
            DeliveryStreamName=stream_name,
            Records=records
        )
        if response['FailedPutCount'] > 0:
            print(f"Warning: {response['FailedPutCount']} records failed to put.")
        else:
            print(f"Successfully put batch of {len(records)} records.")

def main():
    parser = argparse.ArgumentParser(description="Generate mock CloudTrail logs.")
    parser.add_argument("--stream", type=str, help="AWS Kinesis Firehose Delivery Stream name")
    args = parser.parse_args()

    logs = generate_all_logs()

    if args.stream:
        send_to_firehose(logs, args.stream)
        print("Data successfully streamed to Kinesis Data Firehose.")
    else:
        # Write to a local file
        filename = f"cloudtrail_logs_{int(time.time())}.json"
        with open(filename, 'w') as f:
            for log in logs:
                f.write(json.dumps(log) + '\n')
        print(f"Generated {len(logs)} logs and saved to {filename}.")
        print("Tip: Run with --stream <stream_name> to push directly to AWS Kinesis Firehose.")

if __name__ == "__main__":
    main()

import json
import uuid
import random
import time
import os
import argparse
from datetime import datetime, timedelta

# Configuration
NUM_NORMAL_LOGS = 100
NUM_ANOMALIES = 5
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "raw")

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
    for i in range(NUM_ANOMALIES):
        user = "alice_anomaly" + str(i)
        
        login1_time = base_time + timedelta(hours=i)
        login1 = generate_log_entry(user, "203.0.113.1", "US", login1_time)
        
        login2_time = login1_time + timedelta(minutes=5)
        login2 = generate_log_entry(user, "198.51.100.1", "RU", login2_time)
        
        logs.append(login1)
        logs.append(login2)

    logs.sort(key=lambda x: x['eventTime'])
    return logs

def main():
    parser = argparse.ArgumentParser(description="Generate mock CloudTrail logs.")
    parser.add_argument("--output", type=str, default=OUTPUT_DIR, help="Output directory for JSON logs")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)
    logs = generate_all_logs()

    # Write to a local file
    filename = os.path.join(args.output, f"cloudtrail_logs_{int(time.time())}.json")
    with open(filename, 'w') as f:
        for log in logs:
            f.write(json.dumps(log) + '\n')
            
    print(f"Generated {len(logs)} logs and saved to {filename}.")

if __name__ == "__main__":
    main()

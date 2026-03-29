import pytest
from datetime import datetime
from generate_logs import generate_all_logs, generate_log_entry, NUM_NORMAL_LOGS, NUM_ANOMALIES

def test_generate_log_entry():
    now = datetime.utcnow()
    log = generate_log_entry("testuser", "1.2.3.4", "US", now)
    
    assert log["userIdentity"]["userName"] == "testuser"
    assert log["sourceIPAddress"] == "1.2.3.4"
    assert log["country"] == "US"
    assert log["eventName"] == "ConsoleLogin"
    assert "eventVersion" in log

def test_generate_all_logs_contains_anomalies():
    logs = generate_all_logs()
    
    # Expected length: 100 normal logs + (5 anomalies * 2 logs each)
    expected_length = NUM_NORMAL_LOGS + (NUM_ANOMALIES * 2)
    assert len(logs) == expected_length
    
    # Check that anomalies exist
    anomaly_users = [log["userIdentity"]["userName"] for log in logs if "alice_anomaly" in log["userIdentity"]["userName"]]
    
    assert len(anomaly_users) == NUM_ANOMALIES * 2

def test_anomaly_logic_is_valid():
    logs = generate_all_logs()
    
    # Sort strictly chronologically to ensure log1 is before log2
    alice0_logs = sorted([log for log in logs if log["userIdentity"]["userName"] == "alice_anomaly0"], key=lambda x: x["eventTime"])
    
    assert len(alice0_logs) == 2
    
    log1, log2 = alice0_logs[0], alice0_logs[1]
    
    # Verify different IPs and Countries
    assert log1["country"] == "US"
    assert log2["country"] == "RU"
    assert log1["sourceIPAddress"] != log2["sourceIPAddress"]

    # Calculate time difference
    t1 = datetime.strptime(log1["eventTime"], '%Y-%m-%dT%H:%M:%SZ')
    t2 = datetime.strptime(log2["eventTime"], '%Y-%m-%dT%H:%M:%SZ')
    
    diff_minutes = (t2 - t1).total_seconds() / 60
    
    # The anomaly is defined explicitly as a 5 minute difference
    assert diff_minutes == 5.0

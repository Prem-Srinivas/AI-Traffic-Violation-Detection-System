import json
import smtplib
from email.message import EmailMessage
from datetime import datetime
import os

def load_driver_registry():
    try:
        with open('drivers.json', 'r') as f:
            registry = json.load(f)
            registry["DEFAULT"] = {"name": "Unknown Driver", "phone": "+10000000000", "email": "driver@example.com"}
            return registry
    except Exception as e:
        print(f"Warning: Could not load drivers.json dataset - {e}")
        return {"DEFAULT": {"name": "Unknown Driver", "phone": "+10000000000", "email": "driver@example.com"}}

def send_sms(phone_number, message):
    """
    Simulates sending an SMS alert to the driver.
    In real usage this would connect to the Twilio API.
    """
    print(f"\n[SMS DISPATCHED to {phone_number}]")
    print(f"Message:\n{message}")
    print("-" * 40 + "\n")

def send_email(email_address, subject, body):
    """
    Simulates sending an Email alert to the driver.
    (Can be plugged with smtplib.SMTP/Gmail API for real emails)
    """
    print(f"\n[EMAIL DISPATCHED to {email_address}]")
    print(f"Subject: {subject}")
    print(f"Body:\n{body}")
    print("-" * 40 + "\n")

def trigger_alert(violation_data):
    """
    Orchestrates alerts including console, log, SMS, and Email.
    """
    timestamp = datetime.now().strftime("%H:%M")
    v_type = violation_data.get('violation_type', 'Unknown')
    plate = violation_data.get('plate_number', 'N/A')
    camera = violation_data.get('camera', 'CAM_1')
    location = violation_data.get('location', 'Chennai')
    
    # Lookup driver details based on plate
    registry = load_driver_registry()
    driver_info = registry.get(plate, registry["DEFAULT"])
    owner_name = driver_info["name"]
    phone = driver_info["phone"]
    email = driver_info["email"]
    
    # Log to console
    print(f"[{timestamp}] [{camera}] Violation: {v_type} | Plate: {plate} | Owner: {owner_name}")
    
    # Notification Message formats
    sms_message = f"Traffic violation detected.\nVehicle: {plate}\nViolation: {v_type}\nFine: ₹500"
    
    email_body = f"Vehicle Number: {plate}\nViolation: {v_type}\nLocation: {location}\nTime: {timestamp} AM\n\nPlease follow traffic rules."
    
    # Send SMS & Email
    send_sms(phone, sms_message)
    send_email(email, "Traffic Violation Alert", email_body)
    
    # Save to JSON log
    with open("alerts_log.json", "a") as f:
        log_entry = {**violation_data, "system_timestamp": timestamp, "owner_contacted": True}
        f.write(json.dumps(log_entry) + "\n")

def check_for_violations(detections, speeds, frame=None):
    """
    Advanced violation checking logic.
    """
    violations = []
    
    # 1. Speeding Detection
    for id, speed in speeds.items():
        if speed > 100: # Example limit
            violations.append({
                "violation_type": "Speeding",
                "speed": speed,
                "vehicle_id": id,
                "confidence": 0.92
            })

    # 2. Triple Riding & Helmet Detection (Simulated)
    bike_count = 0
    person_count = 0
    for det in detections:
        label = det['label']
        if label == "motorcycle":
            bike_count += 1
        if label == "person":
            person_count += 1
            
    if bike_count > 0:
        # Check for Triple Riding
        if person_count > 2:
            violations.append({
                "violation_type": "Triple Riding",
                "details": f"Persons: {person_count}",
                "confidence": 0.88
            })
        
        # Simulate No Helmet Detection (In real dev, this would be a YOLO detection)
        # For this demo, we'll flag any bike if we 'randomly' decide (placeholder logic)
        import random
        if random.random() < 0.05: # 5% chance to simulate a no-helmet catch in demo
             violations.append({
                "violation_type": "No Helmet",
                "details": "Rider detected without helmet",
                "confidence": 0.95
            })
        
    return violations

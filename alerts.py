import json
import smtplib
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import os

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# --- Permanent alert recipient (from .env or hardcoded fallback) ---
ALERT_PHONE = os.environ.get('ALERT_PHONE', '+919014390204')
ALERT_EMAIL = os.environ.get('ALERT_EMAIL', 'pream4227@gmail.com')

def load_driver_registry():
    try:
        with open('drivers.json', 'r') as f:
            registry = json.load(f)
            registry["DEFAULT"] = {"name": "Unknown Driver", "phone": ALERT_PHONE, "email": ALERT_EMAIL}
            return registry
    except Exception as e:
        print(f"Warning: Could not load drivers.json dataset - {e}")
        return {"DEFAULT": {"name": "Unknown Driver", "phone": ALERT_PHONE, "email": ALERT_EMAIL}}

def send_sms(phone_number, message):
    """
    Sends an SMS alert via Fast2SMS (Indian numbers).
    Always also sends to the permanent admin contact (ALERT_PHONE).
    """
    import requests as req

    targets = list({phone_number.replace('+91','').replace('+',''), 
                    ALERT_PHONE.replace('+91','').replace('+','')})  # deduplicate, strip country code

    api_key = os.environ.get('FAST2SMS_API_KEY', '').strip()

    for target in targets:
        print(f"\n[SMS -> +91{target}]\n{message}\n" + "-"*40)
        if api_key and not api_key.startswith('YOUR'):
            try:
                url = "https://www.fast2sms.com/dev/bulkV2"
                headers = {
                    "authorization": api_key,
                    "Content-Type": "application/x-www-form-urlencoded"
                }
                payload = {
                    "route": "q",
                    "message": message,
                    "language": "english",
                    "flash": 0,
                    "numbers": target
                }
                response = req.post(url, headers=headers, data=payload, timeout=10)
                result = response.json()
                if result.get("return") == True:
                    print(f"[SMS SENT] to +91{target}")
                else:
                    print(f"[SMS FAILED] {result.get('message', result)}")
            except Exception as e:
                print(f"[SMS ERROR] {e}")
        else:
            print(f"[SMS SIMULATED] Fast2SMS key not configured.")

def send_email(email_address, subject, body, html=None):
    """
    Sends a personalized Email alert.
    - email_address : driver's own email (set in To:)
    - ALERT_EMAIL   : admin always gets a Cc:
    - html          : optional rich HTML version
    """
    smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port   = int(os.environ.get('SMTP_PORT', 587))
    smtp_user   = os.environ.get('SMTP_USERNAME', '').strip()
    smtp_pass   = os.environ.get('SMTP_PASSWORD', '').strip()

    all_targets = list({email_address, ALERT_EMAIL})  # deduplicate
    print(f"\n[EMAIL -> {', '.join(all_targets)}] Subject: {subject}")

    if smtp_user and smtp_pass and not smtp_pass.startswith('YOUR'):
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From']    = f"Traffic Alert System <{smtp_user}>"
            msg['To']      = email_address
            if ALERT_EMAIL != email_address:
                msg['Cc'] = ALERT_EMAIL

            msg.attach(MIMEText(body, 'plain'))
            if html:
                msg.attach(MIMEText(html, 'html'))

            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_user, all_targets, msg.as_string())
            print(f"[EMAIL SENT] to {', '.join(all_targets)}")
        except Exception as e:
            print(f"[EMAIL FAILED] {e}")
    else:
        print(f"[EMAIL SIMULATED] SMTP not configured. Would send to {', '.join(all_targets)}")

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
# Fine per violation type (Rs.)
FINE_MAP = {
    "Over-speeding":                1000,
    "No Helmet":                     500,
    "Multiple No Helmets":          1000,
    "Triple Riding":                1000,
    "Signal jumping":                500,
    "Wrong-side driving":            500,
    "No Seatbelt (Driver)":          500,
    "No Seatbelt (Passenger)":       500,
    "Mobile Phone Usage":           1500,
    "Illegal parking":               500,
    "Lane violation":                500,
    "Number plate not visible":      500,
    "Number plate missing/unclear":  500,
    "Headlights off at night":       500,
}

def trigger_alert(violation_data):
    """
    Sends a personalised SMS + Email to the detected vehicle's registered owner
    based on plate lookup from drivers.json. Admin (ALERT_EMAIL) is always CC'd.
    """
    now       = datetime.now()
    timestamp = now.strftime("%H:%M")
    date_str  = now.strftime("%d %b %Y %H:%M")

    v_type   = violation_data.get('violation_type', 'Unknown')
    plate    = violation_data.get('plate_number', 'N/A')
    camera   = violation_data.get('camera', 'CAM_1')
    location = violation_data.get('location', 'Chennai')
    speed    = violation_data.get('speed', 0)
    fine     = FINE_MAP.get(v_type, 500)

    # Lookup registered owner
    registry     = load_driver_registry()
    driver_info  = registry.get(plate, registry["DEFAULT"])
    owner_name   = driver_info["name"]
    phone        = driver_info["phone"]
    driver_email = driver_info["email"]
    is_known     = plate in registry

    print(f"[{timestamp}][{camera}] {v_type} | {plate} | {owner_name} | {driver_email}")

    # --- Personalised SMS ---
    speed_line = f"Speed: {speed} km/h. " if speed and speed > 0 else ""
    sms_msg = (
        f"Dear {owner_name}, a traffic violation for vehicle {plate} has been recorded. "
        f"Violation: {v_type}. {speed_line}"
        f"Fine: Rs.{fine}. Location: {location}. -- AI Traffic System"
    )

    # --- Personalised plain-text email ---
    speed_txt = f"  Speed       : {speed} km/h\n" if speed and speed > 0 else ""
    email_plain = (
        f"Dear {owner_name},\n\n"
        f"A traffic violation has been recorded for your vehicle.\n\n"
        f"  Vehicle No  : {plate}\n"
        f"  Violation   : {v_type}\n"
        f"{speed_txt}"
        f"  Location    : {location}\n"
        f"  Camera      : {camera}\n"
        f"  Date & Time : {date_str}\n"
        f"  Fine Amount : Rs.{fine}\n\n"
        f"Please visit the traffic authority portal to clear your fine.\n"
        f"-- AI Traffic Violation Detection System"
    )

    # --- Rich HTML email ---
    speed_row = (
        f'<tr style="background:#fff5f5;">'
        f'<td style="padding:11px 16px;color:#888;font-weight:bold;border-bottom:1px solid #f0f0f0;">Speed</td>'
        f'<td style="padding:11px 16px;color:#dc3545;font-weight:bold;border-bottom:1px solid #f0f0f0;">{speed} km/h</td></tr>'
    ) if speed and speed > 0 else ""

    owner_badge = (
        '<span style="background:#28a745;color:#fff;padding:2px 10px;border-radius:20px;font-size:11px;">Registered Owner</span>'
        if is_known else
        '<span style="background:#ffc107;color:#333;padding:2px 10px;border-radius:20px;font-size:11px;">Unknown Vehicle</span>'
    )

    email_html = f"""<html><body style="font-family:Arial,sans-serif;background:#f0f2f5;padding:20px;margin:0;">
  <div style="max-width:620px;margin:auto;background:#fff;border-radius:14px;
              box-shadow:0 4px 20px rgba(0,0,0,.12);overflow:hidden;">
    <div style="background:linear-gradient(135deg,#c0392b,#e74c3c);padding:28px;text-align:center;">
      <h1 style="color:#fff;margin:0;font-size:22px;letter-spacing:1px;">Traffic Violation Alert</h1>
      <p style="color:rgba(255,255,255,.85);margin:8px 0 0;font-size:13px;">AI Traffic Violation Detection System</p>
    </div>
    <div style="padding:26px 30px 10px;">
      <p style="font-size:16px;color:#333;margin:0;">Dear <strong>{owner_name}</strong> &nbsp;{owner_badge}</p>
      <p style="color:#666;font-size:14px;line-height:1.7;margin-top:10px;">
        A traffic violation has been detected for your vehicle. Please review the details and clear your fine promptly.
      </p>
    </div>
    <div style="padding:0 30px 20px;">
      <table style="width:100%;border-collapse:collapse;font-size:14px;">
        <tr>
          <td style="padding:11px 16px;color:#888;font-weight:bold;width:38%;border-bottom:1px solid #f0f0f0;">Vehicle No.</td>
          <td style="padding:11px 16px;color:#333;font-weight:bold;border-bottom:1px solid #f0f0f0;">{plate}</td>
        </tr>
        <tr style="background:#fff5f5;">
          <td style="padding:11px 16px;color:#888;font-weight:bold;border-bottom:1px solid #f0f0f0;">Violation</td>
          <td style="padding:11px 16px;border-bottom:1px solid #f0f0f0;">
            <span style="background:#e74c3c;color:#fff;padding:3px 12px;border-radius:20px;font-size:12px;font-weight:bold;">{v_type}</span>
          </td>
        </tr>
        {speed_row}
        <tr style="background:#f9f9f9;">
          <td style="padding:11px 16px;color:#888;font-weight:bold;border-bottom:1px solid #f0f0f0;">Location</td>
          <td style="padding:11px 16px;color:#333;border-bottom:1px solid #f0f0f0;">{location}</td>
        </tr>
        <tr>
          <td style="padding:11px 16px;color:#888;font-weight:bold;border-bottom:1px solid #f0f0f0;">Camera</td>
          <td style="padding:11px 16px;color:#333;border-bottom:1px solid #f0f0f0;">{camera}</td>
        </tr>
        <tr style="background:#f9f9f9;">
          <td style="padding:11px 16px;color:#888;font-weight:bold;border-bottom:1px solid #f0f0f0;">Date &amp; Time</td>
          <td style="padding:11px 16px;color:#333;border-bottom:1px solid #f0f0f0;">{date_str}</td>
        </tr>
        <tr>
          <td style="padding:11px 16px;color:#888;font-weight:bold;">Fine Amount</td>
          <td style="padding:11px 16px;color:#c0392b;font-size:20px;font-weight:bold;">Rs.{fine}</td>
        </tr>
      </table>
    </div>
    <div style="padding:10px 30px 28px;text-align:center;">
      <a href="http://localhost:5000/pay?plate={plate}"
         style="display:inline-block;background:#e74c3c;color:#fff;padding:13px 32px;
                border-radius:8px;text-decoration:none;font-weight:bold;font-size:14px;">
        Pay Online Now &rarr;
      </a>
    </div>
    <div style="background:#f8f9fa;border-top:1px solid #eee;padding:16px;text-align:center;
                font-size:12px;color:#aaa;">
      AI Traffic Violation Detection System &nbsp;|&nbsp; {date_str}
    </div>
  </div>
</body></html>"""

    # Send SMS + personalised email (driver in To:, admin in Cc:)
    send_sms(phone, sms_msg)
    send_email(
        driver_email,
        f"Traffic Violation Notice - {plate} [{v_type}]",
        email_plain,
        html=email_html
    )

    # Save to log
    with open("alerts_log.json", "a") as f:
        log_entry = {
            **violation_data,
            "owner_name":  owner_name,
            "owner_email": driver_email,
            "fine":        fine,
            "timestamp":   date_str,
            "notified":    True
        }
        f.write(json.dumps(log_entry) + "\n")


def check_for_violations(detections, speeds, frame=None):
    """
    Advanced violation checking logic. Incorporates simulation for advanced conditions 
    where dedicated ML models might not be fully operational.
    """
    import random
    from datetime import datetime
    
    violations = []
    
    # 1. Over-speeding Detection (For both bikes and cars)
    for id, speed in speeds.items():
        if speed > 60: # Limit set for detection
            violations.append({
                "violation_type": "Over-speeding",
                "speed": speed,
                "vehicle_id": id,
                "confidence": 0.92
            })

    # Evaluated detections for specific conditions
    for det in detections:
        label = det['label']
        
        if label == "motorcycle":
            # --- Bike Conditions ---
            # Simulated No Helmet detection for testing alerts
            if random.random() < 0.003:
                violations.append({"violation_type": "No Helmet", "det": det})
            # Helmet conditions are partially handled in main.py, but we handle "Multiple No Helmets" here
            no_helmets_count = len(det.get('no_helmets', []))
            if no_helmets_count > 1:
                violations.append({"violation_type": "Multiple No Helmets", "det": det})
                
            # Triple riding prediction (using size / proportion estimation or simulated)
            if random.random() < 0.002: # Simulated low probability
                violations.append({"violation_type": "Triple Riding", "det": det})
                
            # Deterministic backup for Triple Riding
            total_persons = sum(1 for d in detections if d['label'] == 'person')
            total_bikes = sum(1 for d in detections if d['label'] == 'motorcycle')
            if total_bikes > 0 and (total_persons / total_bikes) > 2.5:
                # Limit one per frame to avoid spam
                if not any(v.get('violation_type') == 'Triple Riding' for v in violations):
                     violations.append({"violation_type": "Triple Riding", "det": det})
                
            # Wrong-side driving
            if random.random() < 0.001:
                violations.append({"violation_type": "Wrong-side driving", "det": det})
                
            # Signal jumping
            if random.random() < 0.001:
                violations.append({"violation_type": "Signal jumping", "det": det})
                
            # Illegal parking (e.g. if speed is 0, but we use random simulation here)
            if random.random() < 0.001:
                violations.append({"violation_type": "Illegal parking", "det": det})
                
            # Number plate visibility
            if random.random() < 0.002:
                violations.append({"violation_type": "Number plate not visible", "det": det})
                
            # Mobile phone usage while driving
            if random.random() < 0.001:
                violations.append({"violation_type": "Mobile Phone Usage", "det": det})

        elif label in ["car", "bus", "truck"]:
            # --- Car Conditions ---
            
            # Seatbelt (driver / passenger)
            if random.random() < 0.002:
                violations.append({"violation_type": "No Seatbelt (Driver)", "det": det})
            if random.random() < 0.001:
                violations.append({"violation_type": "No Seatbelt (Passenger)", "det": det})
                
            # Signal jumping
            if random.random() < 0.001:
                violations.append({"violation_type": "Signal jumping", "det": det})
                
            # Wrong-side driving
            if random.random() < 0.001:
                violations.append({"violation_type": "Wrong-side driving", "det": det})
                
            # Illegal parking
            if random.random() < 0.001:
                violations.append({"violation_type": "Illegal parking", "det": det})
                
            # Mobile phone usage
            if random.random() < 0.001:
                violations.append({"violation_type": "Mobile Phone Usage", "det": det})
                
            # Number plate missing / unclear
            if random.random() < 0.002:
                violations.append({"violation_type": "Number plate missing/unclear", "det": det})
                
            # Lane violation
            if random.random() < 0.001:
                violations.append({"violation_type": "Lane violation", "det": det})
                
            # Headlights off during night driving
            current_hour = datetime.now().hour
            if (current_hour >= 18 or current_hour <= 6) and random.random() < 0.002:
                violations.append({"violation_type": "Headlights off at night", "det": det})

    return violations

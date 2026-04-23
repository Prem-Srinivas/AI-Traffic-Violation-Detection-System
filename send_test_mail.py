"""
Test script - sends a real traffic violation alert email using credentials from .env
"""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
smtp_port   = int(os.environ.get('SMTP_PORT', 587))
smtp_user   = os.environ.get('SMTP_USERNAME', '').strip()
smtp_pass   = os.environ.get('SMTP_PASSWORD', '').strip()
alert_email = os.environ.get('ALERT_EMAIL', 'pream4227@gmail.com')

print(f"SMTP User : {smtp_user}")
print(f"Recipient : {alert_email}")
print(f"Connecting to {smtp_server}:{smtp_port} ...")

now = datetime.now().strftime('%d %b %Y %H:%M:%S')

subject = "🚦 Traffic Violation Alert - Test Notification"
plain_body = f"""Dear Admin,

This is a TEST alert from the AI Traffic Violation Detection System.

Violation Details:
  Vehicle      : TN01AB1234
  Violation    : Over-speeding (87 km/h in 60 km/h zone)
  Location     : Anna Salai, Chennai
  Camera       : CAM_1
  Date & Time  : {now}
  Fine Amount  : ₹1,000

Please review the violation on the dashboard.

-- AI Traffic Violation Detection System"""

html_body = f"""
<html><body style="font-family:Arial,sans-serif;background:#f4f4f4;padding:20px;margin:0;">
  <div style="max-width:600px;margin:auto;background:#fff;border-radius:12px;
              box-shadow:0 4px 16px rgba(0,0,0,.12);overflow:hidden;">

    <!-- Header -->
    <div style="background:linear-gradient(135deg,#dc3545,#b02a37);padding:28px;text-align:center;">
      <h1 style="color:#fff;margin:0;font-size:24px;letter-spacing:1px;">
        🚦 Traffic Violation Alert
      </h1>
      <p style="color:rgba(255,255,255,.8);margin:6px 0 0;font-size:13px;">
        AI Traffic Violation Detection System
      </p>
    </div>

    <!-- Body -->
    <div style="padding:30px;">
      <p style="font-size:16px;color:#333;margin-top:0;">Dear Admin,</p>
      <p style="color:#555;font-size:14px;line-height:1.6;">
        A traffic violation has been detected and recorded by the system. Details are below:
      </p>

      <!-- Details Table -->
      <table style="width:100%;border-collapse:collapse;margin:20px 0;font-size:14px;">
        <tr style="background:#fff5f5;">
          <td style="padding:12px 16px;color:#888;font-weight:bold;width:40%;border-bottom:1px solid #f0f0f0;">Vehicle</td>
          <td style="padding:12px 16px;color:#333;border-bottom:1px solid #f0f0f0;">TN01AB1234</td>
        </tr>
        <tr>
          <td style="padding:12px 16px;color:#888;font-weight:bold;border-bottom:1px solid #f0f0f0;">Violation</td>
          <td style="padding:12px 16px;border-bottom:1px solid #f0f0f0;">
            <span style="background:#dc3545;color:#fff;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:bold;">
              Over-speeding
            </span>
            &nbsp; 87 km/h in 60 km/h zone
          </td>
        </tr>
        <tr style="background:#fff5f5;">
          <td style="padding:12px 16px;color:#888;font-weight:bold;border-bottom:1px solid #f0f0f0;">Location</td>
          <td style="padding:12px 16px;color:#333;border-bottom:1px solid #f0f0f0;">Anna Salai, Chennai</td>
        </tr>
        <tr>
          <td style="padding:12px 16px;color:#888;font-weight:bold;border-bottom:1px solid #f0f0f0;">Camera</td>
          <td style="padding:12px 16px;color:#333;border-bottom:1px solid #f0f0f0;">CAM_1</td>
        </tr>
        <tr style="background:#fff5f5;">
          <td style="padding:12px 16px;color:#888;font-weight:bold;border-bottom:1px solid #f0f0f0;">Date & Time</td>
          <td style="padding:12px 16px;color:#333;border-bottom:1px solid #f0f0f0;">{now}</td>
        </tr>
        <tr>
          <td style="padding:12px 16px;color:#888;font-weight:bold;">Fine Amount</td>
          <td style="padding:12px 16px;color:#dc3545;font-size:18px;font-weight:bold;">₹1,000</td>
        </tr>
      </table>

      <a href="http://localhost:5000/challans"
         style="display:inline-block;background:#dc3545;color:#fff;padding:12px 28px;
                border-radius:8px;text-decoration:none;font-weight:bold;font-size:14px;margin-top:10px;">
        View on Dashboard →
      </a>
    </div>

    <!-- Footer -->
    <div style="background:#f8f9fa;padding:16px;text-align:center;
                border-top:1px solid #eee;font-size:12px;color:#aaa;">
      AI Traffic Violation Detection System &nbsp;·&nbsp; {now}
    </div>
  </div>
</body></html>
"""

try:
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From']    = smtp_user
    msg['To']      = alert_email

    msg.attach(MIMEText(plain_body, 'plain'))
    msg.attach(MIMEText(html_body, 'html'))

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, [alert_email], msg.as_string())

    print(f"\n[SUCCESS] Email sent successfully to {alert_email}!")
    print("Check your inbox (and Spam folder just in case).")

except Exception as e:
    print(f"\n[FAILED] Could not send email: {e}")

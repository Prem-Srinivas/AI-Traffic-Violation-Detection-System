import os
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

to_number = os.environ.get('ALERT_PHONE', '+919014390204').strip()

message = (
    "ALERT: Traffic Violation Detected! "
    "Vehicle: TN01AB1234 | Violation: Over-speeding (87 km/h) | "
    "Location: Anna Salai, Chennai | Fine: Rs.1000 "
    "-- AI Traffic Violation System"
)

print(f"Sending SMS to: {to_number}")
print(f"Message:\n{message}\n")

# --- Textbelt (1 free SMS/day, no signup) ---
url = "https://textbelt.com/text"
payload = {
    "phone": to_number,
    "message": message,
    "key": "textbelt"        # "textbelt" = free tier (1/day)
}

try:
    print("Sending via Textbelt (free tier)...")
    response = requests.post(url, data=payload, timeout=15)
    result = response.json()
    print(f"Response: {result}")

    if result.get("success"):
        print(f"\n[SUCCESS] SMS sent to {to_number}!")
        print(f"Remaining today: {result.get('quotaRemaining', 'N/A')} SMS")
    else:
        err = result.get("error", "Unknown error")
        print(f"\n[FAILED] Textbelt: {err}")

        if "quota" in err.lower():
            print("\nFree quota (1/day) exhausted. Options:")
            print("  - Buy Textbelt credits at https://textbelt.com")
            print("  - Recharge Fast2SMS Rs.100 at https://www.fast2sms.com/dashboard/recharge")

except Exception as e:
    print(f"\n[ERROR] {e}")

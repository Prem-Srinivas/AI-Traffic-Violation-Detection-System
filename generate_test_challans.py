import sqlite3
from datetime import datetime, timedelta
import random

db_name = "traffic_violations.db"
conn = sqlite3.connect(db_name)
cursor = conn.cursor()

mock_violations = [
    ("No Helmet", "motorcycle", "TN87AB1234", 45, "Sector 7 Junction"),
    ("Triple Riding", "motorcycle", "KA09XY9999", 55, "Main Boulevard"),
    ("Over-speeding", "car", "MH12CD4567", 120, "Highway Post 42"),
    ("Wrong-side driving", "car", "DL4CBA9876", 30, "Downtown One-Way"),
    ("Signal jumping", "truck", "GJ01ZZ1111", 40, "MG Road Crossing"),
    ("Illegal parking", "car", "TS09AA2222", 0, "No Parking Zone 3")
]

fine_map = {
    "No Helmet": 500,
    "Triple Riding": 1500,
    "Over-speeding": 2000,
    "Wrong-side driving": 3000,
    "Signal jumping": 1000,
    "Illegal parking": 500
}

statuses = ['Paid', 'Unpaid', 'Pending']

print("Generating mock challans...")
for i in range(15):
    v = random.choice(mock_violations)
    
    # Randomize time in the last 7 days
    past_time = datetime.now() - timedelta(days=random.randint(0, 7), hours=random.randint(0, 23))
    ts = past_time.strftime("%Y-%m-%d %H:%M:%S")
    
    # 1. Insert Violation
    cursor.execute('''
        INSERT INTO violations (timestamp, violation_type, vehicle_type, plate_number, speed, location)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (ts, v[0], v[1], v[2], v[3], v[4]))
    violation_id = cursor.lastrowid
    
    # 2. Insert Challan
    fine = fine_map.get(v[0], 500)
    due_date = (past_time + timedelta(days=15)).strftime("%Y-%m-%d %H:%M:%S")
    
    # Weight it more towards Unpaid/Pending to make the charts look balanced
    status = random.choice(['Paid', 'Unpaid', 'Unpaid', 'Pending'])
    
    cursor.execute('''
        INSERT INTO challans (violation_id, plate_number, fine_amount, generated_at, due_date, status)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (violation_id, v[2], fine, ts, due_date, status))

conn.commit()
conn.close()
print("Mock data generated successfully.")

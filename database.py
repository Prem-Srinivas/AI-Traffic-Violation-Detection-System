import sqlite3
from datetime import datetime

class TrafficDB:
    def __init__(self, db_name="traffic_violations.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_table()

    def create_table(self):
        cursor = self.conn.cursor()
        
        # 1. Users Table (Authentication)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT,
                role TEXT
            )
        ''')
        
        # 2. Vehicles Table (Tracking)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vehicles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plate_number TEXT UNIQUE,
                vehicle_type TEXT,
                owner_name TEXT,
                owner_contact TEXT,
                owner_email TEXT,
                registration_date TEXT
            )
        ''')

        # 3. Violations Table (Already exists, updated)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS violations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                violation_type TEXT,
                vehicle_type TEXT,
                plate_number TEXT,
                speed INTEGER,
                camera_id TEXT,
                location TEXT DEFAULT 'Chennai',
                image_path TEXT
            )
        ''')

        # 4. Challans Table (Billing/Fines)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS challans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                violation_id INTEGER,
                plate_number TEXT,
                fine_amount REAL,
                status TEXT DEFAULT 'Unpaid',
                generated_at TEXT,
                due_date TEXT,
                pdf_path TEXT,
                FOREIGN KEY (violation_id) REFERENCES violations(id)
            )
        ''')

        # 5. Payments Table (Transactions)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                challan_id INTEGER,
                amount_paid REAL,
                payment_date TEXT,
                transaction_id TEXT,
                payment_method TEXT,
                FOREIGN KEY (challan_id) REFERENCES challans(id)
            )
        ''')

        # 6. Alerts & Notifications Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                violation_id INTEGER,
                alert_type TEXT,
                message TEXT,
                timestamp TEXT,
                status TEXT DEFAULT 'Unread',
                FOREIGN KEY (violation_id) REFERENCES violations(id)
            )
        ''')
        
        # 7. Notifications (General system notifications)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                title TEXT,
                message TEXT,
                created_at TEXT,
                is_read BOOLEAN DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        # 8. Reports Table (Generated documents)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_name TEXT,
                report_type TEXT,
                generated_by INTEGER,
                generated_at TEXT,
                file_path TEXT,
                FOREIGN KEY (generated_by) REFERENCES users(id)
            )
        ''')

        # 9. Settings Table (Admin config)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_key TEXT UNIQUE,
                setting_value TEXT
            )
        ''')

        # Add default users if table empty
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO users (username, password, role) VALUES ('admin', 'admin123', 'admin')")
            cursor.execute("INSERT INTO users (username, password, role) VALUES ('police', 'police123', 'police')")
        
        self.conn.commit()

    def log_violation(self, type, vehicle, plate, speed, location='Chennai'):
        cursor = self.conn.cursor()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 1. Insert Violation
        cursor.execute('''
            INSERT INTO violations (timestamp, violation_type, vehicle_type, plate_number, speed, location)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (timestamp, type, vehicle, plate, speed, location))
        violation_id = cursor.lastrowid
        
        # 2. Map Violation Type to Fine Amount
        fine_map = {
            "Multiple No Helmets": 1000,
            "No Helmet": 500,
            "Triple Riding": 1500,
            "Speeding": 2000,
            "Over-speeding": 2000,
            "Wrong-side driving": 3000,
            "Signal jumping": 1000,
            "Illegal parking": 500,
            "Number plate not visible": 2500,
            "Number plate missing/unclear": 2500,
            "Mobile Phone Usage": 2000,
            "No Seatbelt (Driver)": 1000,
            "No Seatbelt (Passenger)": 500,
            "Lane violation": 500,
            "Headlights off at night": 500
        }
        fine_amount = fine_map.get(type, 500) # Default to 500
        
        # 3. Create active Challan
        from datetime import timedelta
        due_date = (datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute('''
            INSERT INTO challans (violation_id, plate_number, fine_amount, generated_at, due_date)
            VALUES (?, ?, ?, ?, ?)
        ''', (violation_id, plate, fine_amount, timestamp, due_date))
        
        self.conn.commit()
        return violation_id

def save_violation(type, vehicle, plate, speed, location='Chennai'):
    db = TrafficDB()
    return db.log_violation(type, vehicle, plate, speed, location)

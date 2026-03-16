import sqlite3
from datetime import datetime

class TrafficDB:
    def __init__(self, db_name="traffic_violations.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_table()

    def create_table(self):
        cursor = self.conn.cursor()
        # Violations Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS violations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                violation_type TEXT,
                vehicle_type TEXT,
                plate_number TEXT,
                speed INTEGER,
                camera_id TEXT,
                location TEXT DEFAULT 'Chennai'
            )
        ''')
        # Users Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT,
                role TEXT
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
        cursor.execute('''
            INSERT INTO violations (timestamp, violation_type, vehicle_type, plate_number, speed, location)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (timestamp, type, vehicle, plate, speed, location))
        self.conn.commit()

def save_violation(type, vehicle, plate, speed, location='Chennai'):
    db = TrafficDB()
    db.log_violation(type, vehicle, plate, speed, location)

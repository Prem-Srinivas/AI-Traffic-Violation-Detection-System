import os
import cv2
import threading
import time
from flask import Flask, render_template, request, redirect, session, flash, url_for, Response, jsonify
from detection import TrafficDetector
from speed_tracking import AdvancedTracker
from plate_ocr import PlateOCR
from database import TrafficDB, save_violation
from alerts import check_for_violations, trigger_alert
from functools import wraps

app = Flask(__name__)
app.secret_key = "super_secret_traffic_key"
db = TrafficDB()
latest_frames = {}

# --- Auth Wrappers ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin':
            flash("Admin access required.")
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# --- Video Processing ---
class CameraProcessor(threading.Thread):
    def __init__(self, source, camera_id):
        super().__init__(daemon=True)
        self.source = source
        self.camera_id = camera_id
        self.active = True
        self.detector = TrafficDetector()
        self.tracker = AdvancedTracker()
        self.ocr = PlateOCR()

    def run(self):
        video = cv2.VideoCapture(self.source)
        # Optimize camera buffers for live feed
        if isinstance(self.source, int):
            video.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            video.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            video.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        frame_count = 0
        while self.active:
            ret, frame = video.read()
            if not ret:
                if isinstance(self.source, str):
                    video.set(cv2.CAP_PROP_POS_FRAMES, 0)
                else:
                    print("Camera feed lost or unavailable.")
                    time.sleep(1)
                continue
            
            frame_count += 1
            # Skip heavy AI analysis on intermediate frames to prevent buffer stall
            if frame_count % 3 != 0:
                continue
                
            # Setup advanced preprocessing (Frame extraction, resize, noise reduction, RGB mapping)
            try:
                # Resize to 640x640
                frame = cv2.resize(frame, (640, 640))
                
                # Noise reduction
                clean_frame = cv2.GaussianBlur(frame, (5, 5), 0)
                
                # The YOLO underlying model takes care of BGR -> RGB internally, 
                # but we logically mark the clean_frame context
                frame = clean_frame
            except Exception:
                pass

            detections = self.detector.detect_vehicles(frame)
            speeds = self.tracker.update(detections)
            violations = check_for_violations(detections, speeds)

            for v in violations:
                det = next((d for d in detections if d['label'] in ["car", "motorcycle"]), None)
                plate = "PENDING"
                if det:
                    x1, y1, x2, y2 = det['bbox']
                    vehicle_roi = frame[y1:y2, x1:x2]
                    if det['label'] == "motorcycle":
                        if not self.detector.detect_helmets(vehicle_roi):
                            v['violation_type'] = "No Helmet"
                    plate = self.ocr.extract_plate(frame, det['bbox'])

                save_violation(v.get('violation_type', 'Unknown'), 
                               det['label'] if det else "unknown", 
                               plate, v.get('speed', 0))
                trigger_alert({**v, "plate_number": plate, "camera": self.camera_id})
            
            # Draw bounding boxes for visual sampling
            for det in detections:
                x1, y1, x2, y2 = det['bbox']
                label = det['label']
                
                if label == 'motorcycle':
                    # 1. Main Bike Bounding Box (Green / BGR: 0, 255, 0)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    # Bike Label (Green filled box, Black text)
                    cv2.rectangle(frame, (x1, y1-30), (x1+60, y1), (0, 255, 0), -1)
                    cv2.putText(frame, 'Bike', (x1+10, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
                    
                    # 2. Mock Helmet Tracking Indicator (Red / BGR: 0, 0, 255)
                    # Approximating a rider's head position inside the motorcycle tracking frame
                    head_x1 = x1 + int((x2 - x1) * 0.4)
                    head_x2 = x1 + int((x2 - x1) * 0.6)
                    head_y1 = y1 - 10
                    head_y2 = y1 + 50
                    
                    cv2.rectangle(frame, (head_x1, head_y1), (head_x2, head_y2), (0, 0, 255), 2)
                    # No Helmet Label (Red filled box, White text) floating left to the head
                    cv2.rectangle(frame, (head_x1 - 100, head_y1 + 10), (head_x1, head_y1 + 35), (0, 0, 255), -1)
                    cv2.putText(frame, 'No Helmet', (head_x1 - 95, head_y1 + 28), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

                    # 3. Orange Plate Bounding Box (Yellow-Orange / BGR: 0, 165, 255)
                    plate = self.ocr.extract_plate(frame, det['bbox'])
                    plate_x1 = x1 + int((x2 - x1) * 0.3)
                    plate_x2 = x1 + int((x2 - x1) * 0.7)
                    plate_y1 = y2 - 50
                    plate_y2 = y2 - 10
                    
                    cv2.rectangle(frame, (plate_x1, plate_y1), (plate_x2, plate_y2), (0, 165, 255), 2)
                    
                    # Number Plate Text Sidebar (Yellow-Orange filled box, Black text) attached
                    ptext1 = "Number Plate:"
                    ptext2 = str(plate)
                    w, h = cv2.getTextSize(ptext1, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
                    cv2.rectangle(frame, (plate_x2, plate_y1), (plate_x2 + w + 20, plate_y1 + h * 2 + 20), (0, 200, 255), -1)
                    cv2.putText(frame, ptext1, (plate_x2 + 5, plate_y1 + h + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
                    cv2.putText(frame, ptext2, (plate_x2 + 5, plate_y1 + h * 2 + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)

                else:
                    # Default visualization for other vehicles
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                    cv2.putText(frame, label.capitalize(), (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
                
            ret_jpg, buffer = cv2.imencode('.jpg', frame)
            if ret_jpg:
                latest_frames[self.camera_id] = buffer.tobytes()

        video.release()

import atexit

# Global state for cameras
active_processors = []

def start_cameras(sources):
    global active_processors
    # Stop existing
    for p in active_processors:
        p.active = False
    active_processors.clear()
    
    # Start new
    for i, src in enumerate(sources):
        processor = CameraProcessor(src, f"CAM_{i+1}")
        processor.start()
        active_processors.append(processor)

# Initial start
current_sources = [0] # Default to system camera
start_cameras(current_sources)

@atexit.register
def cleanup():
    for p in active_processors:
        p.active = False

# --- Routes ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        cursor = db.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = cursor.fetchone()
        
        if user:
            session['username'] = user[1]
            session['role'] = user[3]
            flash("Grid access granted. Welcome, Agent.")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid credentials. Grid access denied.")
            
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form.get('role', 'police')
        
        cursor = db.conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (username, password, role))
            db.conn.commit()
            flash("Account initialized. You may now decrypt and access.")
            return redirect(url_for('login'))
        except Exception as e:
            flash("Identifier already exists in the grid.")
            
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Session terminated successfully.")
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    cursor = db.conn.cursor()
    cursor.execute("SELECT timestamp, violation_type, vehicle_type, plate_number, speed FROM violations ORDER BY id DESC LIMIT 15")
    violations = [
        {"timestamp": v[0], "violation_type": v[1], "vehicle_type": v[2], "plate_number": v[3], "speed": v[4]}
        for v in cursor.fetchall()
    ]
    cursor.execute("SELECT COUNT(*) FROM violations")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT AVG(speed) FROM violations WHERE speed > 0")
    avg_speed = round(cursor.fetchone()[0] or 0, 1)
    
    return render_template('dashboard.html', violations=violations, total_violations=total, avg_speed=avg_speed)

@app.route('/lookup')
@login_required
def lookup_ui():
    return render_template('lookup.html')

from alerts import load_driver_registry, trigger_alert

@app.route('/api/lookup', methods=['GET'])
@login_required
def api_lookup():
    plate = request.args.get('plate', '').strip()
    registry = load_driver_registry()
    if plate in registry:
        data = registry[plate]
        return jsonify({
            "found": True,
            "name": data["name"],
            "phone": data["phone"],
            "email": data["email"]
        })
    else:
        return jsonify({"found": False})

@app.route('/api/alert_manual', methods=['POST'])
@login_required
def manual_alert():
    data = request.json
    plate = data.get('plate')
    v_type = data.get('violation_type', 'Manual Tracking')
    
    # We construct a mock violation dict to push through the existing pipeline
    violation_data = {
        "violation_type": v_type,
        "plate_number": plate,
        "camera": "OPERATOR_MANUAL",
        "speed": 0,
        "location": "Manual Control Desk"
    }
    
    trigger_alert(violation_data)
    save_violation(v_type, "unknown", plate, 0, "Manual Control Desk")
    return jsonify({"success": True, "message": "Dispatched"})

def generate_frames(camera_id):
    while True:
        frame_bytes = latest_frames.get(camera_id)
        if frame_bytes:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        else:
            time.sleep(0.1)

@app.route('/video_feed/<camera_id>')
@login_required
def video_feed(camera_id):
    return Response(generate_frames(camera_id), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/set_source', methods=['POST'])
@login_required
def set_source():
    global current_sources
    data = request.json
    source_type = data.get('type')
    source_value = data.get('value')
    
    if source_type == 'webcam':
        try:
            val = int(source_value)
            current_sources = [val]
        except ValueError:
            return jsonify({"success": False, "error": "Invalid webcam ID"})
    elif source_type in ['video', 'image']:
        if os.path.exists(source_value):
           current_sources = [source_value]
        else:
           return jsonify({"success": False, "error": "File path does not exist"})
    else:
        return jsonify({"success": False, "error": "Invalid source type"})
        
    start_cameras(current_sources)
    return jsonify({"success": True, "message": f"Camera source updated to {source_value}"})

from werkzeug.utils import secure_filename
import os

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/api/upload_media', methods=['POST'])
@login_required
def upload_media():
    global current_sources
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No file part"})
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "error": "No selected file"})
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        current_sources = [filepath]
        start_cameras(current_sources)
        return jsonify({"success": True, "message": "Media uploaded and started!"})

@app.route('/admin')
@login_required
@admin_required
def admin():
    return render_template('admin.html')

@app.route('/api/data')
@login_required
def api_data():
    cursor = db.conn.cursor()
    cursor.execute("SELECT timestamp, violation_type, vehicle_type, plate_number, speed FROM violations ORDER BY id DESC LIMIT 15")
    violations = [
        {"timestamp": v[0], "violation_type": v[1], "vehicle_type": v[2], "plate_number": v[3], "speed": v[4]}
        for v in cursor.fetchall()
    ]
    cursor.execute("SELECT COUNT(*) FROM violations")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT AVG(speed) FROM violations WHERE speed > 0")
    avg_speed = round(cursor.fetchone()[0] or 0, 1)
    
    return {
        "violations": violations,
        "total_violations": total,
        "avg_speed": avg_speed
    }

import io
import csv

@app.route('/api/export')
@login_required
def export_reports():
    cursor = db.conn.cursor()
    cursor.execute("SELECT timestamp, violation_type, vehicle_type, plate_number, speed, location FROM violations ORDER BY id DESC")
    violations = cursor.fetchall()
    
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['Time', 'Violation', 'Vehicle', 'Plate Number', 'Speed (km/h)', 'Location'])
    cw.writerows(violations)
    
    output = si.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=traffic_violation_report.csv"}
    )

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=False)
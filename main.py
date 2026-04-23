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
        self.paused = False
        self.seek_command = None

    def run(self):
        if isinstance(self.source, int):
            video = cv2.VideoCapture(self.source, cv2.CAP_DSHOW)
        else:
            video = cv2.VideoCapture(self.source)
        # Optimize camera buffers for live feed
        if isinstance(self.source, int):
            video.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            video.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            video.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        frame_count = 0
        while self.active:
            if self.paused:
                time.sleep(0.1)
                continue

            if self.seek_command:
                current_f = video.get(cv2.CAP_PROP_POS_FRAMES)
                if self.seek_command == 'forward':
                    video.set(cv2.CAP_PROP_POS_FRAMES, current_f + 150)
                elif self.seek_command == 'backward':
                    video.set(cv2.CAP_PROP_POS_FRAMES, max(0, current_f - 150))
                elif self.seek_command == 'restart':
                    video.set(cv2.CAP_PROP_POS_FRAMES, 0)
                self.seek_command = None

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
            no_helmet_boxes = self.detector.detect_no_helmets(frame)

            # Assign no helmet bounding boxes to motorcycle detections
            for det in detections:
                if det['label'] == 'motorcycle':
                    det['no_helmets'] = []
                    x1, y1, x2, y2 = det['bbox']
                    for hx1, hy1, hx2, hy2 in no_helmet_boxes:
                        hcx, hcy = (hx1 + hx2) // 2, (hy1 + hy2) // 2
                        if x1 <= hcx <= x2 and y1 <= hcy <= y2:
                            det['no_helmets'].append([hx1, hy1, hx2, hy2])
            
            violations = check_for_violations(detections, speeds)
            # Add real no-helmet violations
            for det in detections:
                if det.get('no_helmets'):
                    violations.append({
                        "violation_type": "No Helmet",
                        "det": det
                    })

            for v in violations:
                det = v.get('det')
                # Fallback for speed/triple-riding violations that didn't pass a specific det
                if not det:
                    det = next((d for d in detections if d['label'] in ["car", "motorcycle"]), None)
                
                plate = "PENDING"
                if det:
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
                    
                    # 2. No Helmet indicator (Real or Simulated)
                    is_no_helmet = any(v.get('violation_type') == 'No Helmet' and v.get('det') == det for v in violations)
                    if is_no_helmet:
                        # Draw prominent alert around the bike
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
                        # Text background
                        cv2.rectangle(frame, (x1, y1-60), (x1+160, y1-30), (0, 0, 255), -1)
                        cv2.putText(frame, '!!! NO HELMET !!!', (x1+5, y1-40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                    
                    no_helmets = det.get('no_helmets', [])
                    for i, (hx1, hy1, hx2, hy2) in enumerate(no_helmets):
                        cv2.rectangle(frame, (hx1, hy1), (hx2, hy2), (0, 0, 255), 2)
                        # No Helmet Label
                        cv2.rectangle(frame, (hx1 - 100, hy1 + 10), (hx1, hy1 + 35), (0, 0, 255), -1)
                        cv2.putText(frame, 'No Helmet', (hx1 - 95, hy1 + 28), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

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
current_sources = ['videos/traffic.mp4'] # Default to direct video file
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

@app.route('/api/video_control', methods=['POST'])
@login_required
def video_control():
    data = request.json
    action = data.get('action') # 'play', 'pause', 'forward', 'backward', 'restart'
    camera_id = data.get('camera_id', 'CAM_1')
    
    target_processor = next((p for p in active_processors if p.camera_id == camera_id), None)
    if not target_processor:
        return jsonify({"success": False, "error": "Camera not found"})
        
    if action == 'play':
        target_processor.paused = False
    elif action == 'pause':
        target_processor.paused = True
    elif action in ['forward', 'backward', 'restart']:
        target_processor.seek_command = action
        target_processor.paused = False # Resume if seeking
        
    return jsonify({"success": True, "action": action})

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

@app.route('/violations')
@login_required
def view_violations():
    cursor = db.conn.cursor()
    cursor.execute("SELECT timestamp, violation_type, vehicle_type, plate_number, speed FROM violations ORDER BY id DESC LIMIT 100")
    violations = [
        {"timestamp": v[0], "violation_type": v[1], "vehicle_type": v[2], "plate_number": v[3], "speed": v[4]}
        for v in cursor.fetchall()
    ]
    return render_template('violations.html', violations=violations)

@app.route('/api/send_challan_alert', methods=['POST'])
@login_required
def send_challan_alert():
    data = request.json
    challan_id = data.get('challan_id')
    plate = data.get('plate')
    
    if not challan_id:
        return jsonify({"success": False, "error": "Invalid Challan ID"}), 400
        
    registry = load_driver_registry()
    driver_info = registry.get(plate, registry["DEFAULT"])
    owner_name = driver_info["name"]
    phone = driver_info["phone"]
    email = driver_info["email"]
    
    sms_message = f"URGENT: Traffic Challan #{challan_id} issued for vehicle {plate}. Please pay immediately to avoid compounding penalties."
    email_body = f"Dear {owner_name},\n\nA traffic violation has been registered for your vehicle ({plate}).\nChallan ID: #{challan_id}\n\nPlease visit the official portal to review the evidence and clear your pending fines.\n\nSmart Intercept Network"
    
    # Normally this uses the real Twilio/SMTP logic in alerts.py
    # We call these helpers
    try:
        from alerts import send_sms, send_email
        send_sms(phone, sms_message)
        send_email(email, "Official Traffic Challan Notice", email_body)
    except Exception as e:
        print(e)
        
    # Mask contact for UI
    masked_phone = f"{phone[:4]}***{phone[-3:]}"
    masked_email = f"***{email[email.find('@'):]}" if '@' in email else "***@example.com"
        
    return jsonify({
        "success": True, 
        "message": f"Dispatched via Twilio to {masked_phone} & SMTP {masked_email}"
    })

@app.route('/challans', methods=['GET', 'POST'])
@login_required
def manage_challans():
    cursor = db.conn.cursor()
    
    if request.method == 'POST':
        # Update Challan Status
        challan_id = request.form.get('challan_id')
        new_status = request.form.get('status')
        if challan_id and new_status:
            cursor.execute("UPDATE challans SET status=? WHERE id=?", (new_status, challan_id))
            db.conn.commit()
            flash(f"Challan #{challan_id} marked as {new_status}")
            return redirect(url_for('manage_challans'))

    # Build the full joined query
    query = """
        SELECT c.id, v.plate_number, v.vehicle_type, v.violation_type, 
               c.fine_amount, v.timestamp, v.location, c.status, v.image_path
        FROM challans c
        LEFT JOIN violations v ON c.violation_id = v.id
        ORDER BY c.id DESC
    """
    cursor.execute(query)
    challan_records = [
        {
            "id": row[0], "plate": row[1], "vehicle": row[2], "violation": row[3],
            "fine": row[4], "date": row[5], "location": row[6], "status": row[7], "image": row[8]
        }
        for row in cursor.fetchall()
    ]

    # Calculate Totals
    cursor.execute("SELECT SUM(fine_amount) FROM challans WHERE status='Paid'")
    total_paid = cursor.fetchone()[0] or 0.0
    cursor.execute("SELECT SUM(fine_amount) FROM challans WHERE status='Unpaid' OR status='Pending'")
    total_pending = cursor.fetchone()[0] or 0.0

    return render_template('challans.html', challans=challan_records, total_paid=total_paid, total_pending=total_pending)

@app.route('/reports')
@login_required
def reports():
    cursor = db.conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM violations")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT AVG(speed) FROM violations WHERE speed > 0")
    avg_speed = round(cursor.fetchone()[0] or 0, 1)
    cursor.execute("SELECT COUNT(*) FROM violations WHERE violation_type LIKE '%Helmet%'")
    helmet_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM violations WHERE violation_type LIKE '%Speed%'")
    speed_count = cursor.fetchone()[0]
    
    return render_template('reports.html', total_violations=total, avg_speed=avg_speed, helmet_violations=helmet_count, speed_count=speed_count)

@app.route('/alerts')
@login_required
def alerts_list():
    cursor = db.conn.cursor()
    cursor.execute("SELECT timestamp, violation_type, vehicle_type, plate_number, speed, location FROM violations ORDER BY id DESC LIMIT 20")
    alerts = [
        {"timestamp": v[0], "violation_type": v[1], "vehicle_type": v[2], "plate_number": v[3], "speed": v[4], "camera": v[5]}
        for v in cursor.fetchall()
    ]
    return render_template('alerts_list.html', alerts=alerts)

@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html')

# ─────────────────────────────────────────────────────────────
#  PUBLIC PAYMENT PORTAL  (no login required)
# ─────────────────────────────────────────────────────────────
import uuid

@app.route('/pay')
def payment_portal():
    """Public-facing payment page for vehicle owners."""
    return render_template('payment_portal.html')

@app.route('/api/pay/lookup')
def pay_lookup():
    """Look up all challans for a plate number (public, no auth)."""
    plate = request.args.get('plate', '').strip().upper()
    if not plate:
        return jsonify({"found": False})

    cursor = db.conn.cursor()
    cursor.execute("""
        SELECT c.id, v.violation_type, c.fine_amount, c.status,
               v.timestamp, c.due_date, v.location
        FROM challans c
        LEFT JOIN violations v ON c.violation_id = v.id
        WHERE c.plate_number = ?
        ORDER BY c.id DESC
    """, (plate,))
    rows = cursor.fetchall()

    if not rows:
        return jsonify({"found": False})

    # Lookup driver info from registry
    from alerts import load_driver_registry
    registry    = load_driver_registry()
    driver_info = registry.get(plate, {})

    challans = [{
        "id":        r[0],
        "violation": r[1] or "Unknown",
        "fine":      r[2] or 0,
        "status":    r[3] or "Unpaid",
        "date":      r[4],
        "due_date":  r[5],
        "location":  r[6] or "Chennai"
    } for r in rows]

    return jsonify({
        "found":        True,
        "driver_name":  driver_info.get("name", "Vehicle Owner"),
        "driver_email": driver_info.get("email", ""),
        "driver_phone": driver_info.get("phone", ""),
        "challans":     challans
    })

@app.route('/api/pay/challan', methods=['POST'])
def pay_challan():
    """Process a challan payment (public endpoint)."""
    data           = request.json
    challan_id     = data.get('challan_id')
    plate          = data.get('plate', '').upper()
    payment_method = data.get('payment_method', 'UPI')

    if not challan_id:
        return jsonify({"success": False, "error": "Invalid challan ID"}), 400

    cursor = db.conn.cursor()

    # Verify challan belongs to this plate and is unpaid
    cursor.execute("SELECT fine_amount, status FROM challans WHERE id=? AND plate_number=?",
                   (challan_id, plate))
    row = cursor.fetchone()
    if not row:
        return jsonify({"success": False, "error": "Challan not found"}), 404
    if row[1] == 'Paid':
        return jsonify({"success": False, "error": "Already paid"}), 400

    amount = row[0]
    txn_id = "TRF" + uuid.uuid4().hex[:10].upper()
    paid_at = __import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Record payment
    cursor.execute("""
        INSERT INTO payments (challan_id, amount_paid, payment_date, transaction_id, payment_method)
        VALUES (?, ?, ?, ?, ?)
    """, (challan_id, amount, paid_at, txn_id, payment_method))

    # Update challan status
    cursor.execute("UPDATE challans SET status='Paid' WHERE id=?", (challan_id,))
    db.conn.commit()

    # Send receipt email
    try:
        from alerts import load_driver_registry, send_email
        registry    = load_driver_registry()
        driver_info = registry.get(plate, {})
        owner_name  = driver_info.get("name", "Vehicle Owner")
        email_addr  = driver_info.get("email", "")

        if email_addr:
            subject = f"Payment Receipt - Challan #{challan_id} | {txn_id}"
            plain   = (
                f"Dear {owner_name},\n\n"
                f"Your payment has been received successfully.\n\n"
                f"  Challan ID    : #{challan_id}\n"
                f"  Vehicle       : {plate}\n"
                f"  Amount Paid   : Rs.{amount:,.0f}\n"
                f"  Payment Method: {payment_method}\n"
                f"  Transaction ID: {txn_id}\n"
                f"  Date & Time   : {paid_at}\n\n"
                f"Thank you for paying your fine on time.\n"
                f"-- AI Traffic Violation Detection System"
            )
            html = f"""<html><body style="font-family:Arial,sans-serif;background:#f0f2f5;padding:20px;">
  <div style="max-width:600px;margin:auto;background:#fff;border-radius:14px;
              box-shadow:0 4px 20px rgba(0,0,0,.1);overflow:hidden;">
    <div style="background:linear-gradient(135deg,#27ae60,#2ecc71);padding:28px;text-align:center;">
      <h1 style="color:#fff;margin:0;font-size:22px;">Payment Successful</h1>
      <p style="color:rgba(255,255,255,.85);margin:6px 0 0;font-size:13px;">AI Traffic Violation Detection System</p>
    </div>
    <div style="padding:28px;">
      <p style="font-size:16px;">Dear <strong>{owner_name}</strong>,</p>
      <p style="color:#666;font-size:14px;line-height:1.7;margin-top:8px;">
        Your traffic fine has been paid successfully. Here is your receipt:
      </p>
      <table style="width:100%;border-collapse:collapse;font-size:14px;margin-top:20px;">
        <tr style="background:#f9f9f9;"><td style="padding:12px 16px;color:#888;font-weight:bold;width:40%;border-bottom:1px solid #f0f0f0;">Challan ID</td>
            <td style="padding:12px 16px;font-weight:bold;border-bottom:1px solid #f0f0f0;">#{challan_id}</td></tr>
        <tr><td style="padding:12px 16px;color:#888;font-weight:bold;border-bottom:1px solid #f0f0f0;">Vehicle</td>
            <td style="padding:12px 16px;border-bottom:1px solid #f0f0f0;">{plate}</td></tr>
        <tr style="background:#f9f9f9;"><td style="padding:12px 16px;color:#888;font-weight:bold;border-bottom:1px solid #f0f0f0;">Amount Paid</td>
            <td style="padding:12px 16px;color:#27ae60;font-size:20px;font-weight:800;border-bottom:1px solid #f0f0f0;">Rs.{amount:,.0f}</td></tr>
        <tr><td style="padding:12px 16px;color:#888;font-weight:bold;border-bottom:1px solid #f0f0f0;">Payment Method</td>
            <td style="padding:12px 16px;border-bottom:1px solid #f0f0f0;">{payment_method}</td></tr>
        <tr style="background:#f9f9f9;"><td style="padding:12px 16px;color:#888;font-weight:bold;border-bottom:1px solid #f0f0f0;">Transaction ID</td>
            <td style="padding:12px 16px;font-family:monospace;font-weight:bold;border-bottom:1px solid #f0f0f0;">{txn_id}</td></tr>
        <tr><td style="padding:12px 16px;color:#888;font-weight:bold;">Date &amp; Time</td>
            <td style="padding:12px 16px;">{paid_at}</td></tr>
      </table>
    </div>
    <div style="background:#f8f9fa;border-top:1px solid #eee;padding:16px;text-align:center;
                font-size:12px;color:#aaa;">
      AI Traffic Violation Detection System &nbsp;|&nbsp; {paid_at}
    </div>
  </div>
</body></html>"""
            send_email(email_addr, subject, plain, html=html)
    except Exception as e:
        print(f"Receipt email error: {e}")

    return jsonify({"success": True, "transaction_id": txn_id, "amount": amount})

# ─────────────────────────────────────────────────────────────
#  CHALLAN PDF GENERATION & DOWNLOAD
# ─────────────────────────────────────────────────────────────
from flask import send_file
from pdf_generator import generate_challan_pdf

@app.route('/download_challan/<int:challan_id>')
def download_challan(challan_id):
    """Generates and serves a PDF challan document."""
    cursor = db.conn.cursor()
    cursor.execute("""
        SELECT c.id, c.plate_number, v.violation_type, v.vehicle_type, 
               c.fine_amount, v.timestamp, v.location, c.status
        FROM challans c
        JOIN violations v ON c.violation_id = v.id
        WHERE c.id = ?
    """, (challan_id,))
    row = cursor.fetchone()
    
    if not row:
        return "Challan not found", 404
        
    # Lookup owner name from registry
    from alerts import load_driver_registry
    registry = load_driver_registry()
    owner_info = registry.get(row[1], registry["DEFAULT"])
    
    challan_data = {
        "id": row[0],
        "plate": row[1],
        "violation": row[2],
        "vehicle": row[3],
        "fine": row[4],
        "date": row[5],
        "location": row[6],
        "status": row[7],
        "owner_name": owner_info["name"]
    }
    
    # Path to save temp PDF
    pdf_dir = os.path.join(app.root_path, 'static', 'challans')
    filename = f"Challan_{challan_id}_{row[1]}.pdf"
    pdf_path = os.path.join(pdf_dir, filename)
    
    generate_challan_pdf(challan_data, pdf_path)
    
    return send_file(pdf_path, as_attachment=True)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=False)
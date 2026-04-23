from ultralytics import YOLO

model = YOLO("yolov8n.pt")
helmet_model = YOLO("models/helmet_model.pt")

def detect_objects(frame):
    results = model(frame)
    helmet_results = helmet_model(frame)

    detections = []
    persons = []

    # Get standard detections
    for r in results:
        for box in r.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cls = int(box.cls[0])
            label = model.names[cls]
            if label == "person":
                persons.append((x1, y1, x2, y2))
            else:
                detections.append((label, x1, y1, x2, y2))

    # Get helmet detections
    helmets = []
    for r in helmet_results:
        for box in r.boxes:
            cls = int(box.cls[0])
            name = helmet_model.names[cls]
            # Assuming class 0 is hardhat/helmet, or explicitly naming it
            if cls == 0 or 'helmet' in name.lower() or 'hardhat' in name.lower():
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                helmets.append((x1, y1, x2, y2))

    # Map helmets to persons
    for px1, py1, px2, py2 in persons:
        has_helmet = False
        for hx1, hy1, hx2, hy2 in helmets:
            # Check if helmet center is within the person's bounding box
            hcx, hcy = (hx1 + hx2) // 2, (hy1 + hy2) // 2
            if px1 <= hcx <= px2 and py1 <= hcy <= py2:
                # Helmet is on this person
                # Ideally check upper part, but basic overlap is fine
                if hcy < py1 + (py2 - py1) // 2: 
                    has_helmet = True
                    break
        
        if has_helmet:
            detections.append(("person_with_helmet", px1, py1, px2, py2))
        else:
            detections.append(("person_without_helmet", px1, py1, px2, py2))

    return detections
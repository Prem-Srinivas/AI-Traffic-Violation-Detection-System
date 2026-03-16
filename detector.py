from ultralytics import YOLO

model = YOLO("yolov8n.pt")

def detect_objects(frame):

    results = model(frame)

    detections = []

    for r in results:

        boxes = r.boxes

        for box in boxes:

            x1, y1, x2, y2 = map(int, box.xyxy[0])

            cls = int(box.cls[0])

            label = model.names[cls]

            detections.append((label, x1, y1, x2, y2))

    return detections
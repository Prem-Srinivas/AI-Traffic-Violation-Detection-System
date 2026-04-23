from ultralytics import YOLO
import cv2

class TrafficDetector:
    def __init__(self, vehicle_model="models/yolov8n.pt", 
                 helmet_model="models/helmet_model.pt", 
                 plate_model="models/plate_model.pt"):
        
        # Main vehicle detector
        self.vehicle_model = YOLO(vehicle_model)
        
        # Placeholders for advanced models (using n version as fallback or mock)
        # In a real system, these would be trained specifically for these tasks.
        try:
            self.helmet_model = YOLO(helmet_model)
        except:
            print("Warning: Helmet model not found, using vehicle model fallback.")
            self.helmet_model = self.vehicle_model
            
        try:
            self.plate_model = YOLO(plate_model)
        except:
            print("Warning: Plate model not found, using vehicle model fallback.")
            self.plate_model = self.vehicle_model

        self.classes = self.vehicle_model.names

    def detect_vehicles(self, frame):
        results = self.vehicle_model(frame, verbose=False)
        detections = []
        for r in results:
            for box in r.boxes:
                label = self.classes[int(box.cls[0])]
                if label in ["car", "motorcycle", "bus", "truck", "person"]:
                    detections.append({
                        "label": label,
                        "bbox": list(map(int, box.xyxy[0])),
                        "conf": float(box.conf[0])
                    })
        return detections

    def detect_no_helmets(self, frame):
        # Specific helmet detection logic
        results = self.helmet_model(frame, verbose=False)
        no_helmet_boxes = []
        for r in results:
            for box in r.boxes:
                # Class 1 is 'NO-Hardhat' in the downloaded model
                if int(box.cls[0]) == 1 and box.conf[0] > 0.4:
                    no_helmet_boxes.append(list(map(int, box.xyxy[0])))
        return no_helmet_boxes

    def detect_plates(self, vehicle_roi):
        # Specific plate detection logic
        results = self.plate_model(vehicle_roi, verbose=False)
        # Simplified: Find best plate box
        best_plate = None
        for r in results:
            for box in r.boxes:
                if box.conf[0] > 0.5:
                    best_plate = list(map(int, box.xyxy[0]))
                    break
        return best_plate

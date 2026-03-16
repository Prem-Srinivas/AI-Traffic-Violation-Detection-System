import cv2
import hashlib
import json

# Mock OCR returning specific plates for demonstration
class PlateOCR:
    def __init__(self):
        try:
            with open('drivers.json', 'r') as f:
                self.plates_db = list(json.load(f).keys())
        except Exception:
            self.plates_db = [
                "TN10AB1234",
                "AP39CD5678",
                "KA05EF1111",
                "MH14DX8890",
                "DL01ZZ1234"
            ]

    def extract_plate(self, frame, bbox):
        x1, y1, x2, y2 = bbox
        
        # Consistent mapping for the same vehicle over time based on bounding box origins
        pos_str = f"{x1//50}_{y1//50}"
        plate_hash = int(hashlib.md5(pos_str.encode()).hexdigest()[:4], 16)
        
        return self.plates_db[plate_hash % len(self.plates_db)]

def get_plate_number(frame, bbox):
    ocr = PlateOCR()
    return ocr.extract_plate(frame, bbox)

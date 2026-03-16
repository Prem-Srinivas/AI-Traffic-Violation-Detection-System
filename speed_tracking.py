import math
import time

class AdvancedTracker:
    """
    Simulates DeepSORT-like tracking with ID persistence and velocity-based speed estimation.
    """
    def __init__(self, calibration_factor=1.2):
        self.tracks = {} # ID: {center, last_seen, speed_history}
        self.next_id = 100
        self.calibration_factor = calibration_factor # Pixels to km/h mapping

    def update(self, detections):
        current_time = time.time()
        new_tracks = {}

        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            
            # Match with existing tracks (simple distance matching for demo, simulated DeepSORT)
            best_id = None
            min_dist = 50 

            for tid, tdata in self.tracks.items():
                dist = math.hypot(cx - tdata['center'][0], cy - tdata['center'][1])
                if dist < min_dist:
                    min_dist = dist
                    best_id = tid

            if best_id is not None:
                # Update track
                prev_data = self.tracks[best_id]
                dt = current_time - prev_data['last_seen']
                dist_px = math.hypot(cx - prev_data['center'][0], cy - prev_data['center'][1])
                
                # Speed Estimate = (Distance / Time) * Calibration
                instant_speed = (dist_px / dt) * self.calibration_factor if dt > 0 else 0
                
                # Smoothing
                avg_speed = (prev_data.get('avg_speed', 0) * 0.7) + (instant_speed * 0.3)
                
                new_tracks[best_id] = {
                    'center': (cx, cy),
                    'last_seen': current_time,
                    'avg_speed': int(avg_speed),
                    'label': det['label']
                }
            else:
                # New track
                new_tracks[self.next_id] = {
                    'center': (cx, cy),
                    'last_seen': current_time,
                    'avg_speed': 0,
                    'label': det['label']
                }
                self.next_id += 1

        # Cleanup old tracks
        for tid, tdata in self.tracks.items():
            if current_time - tdata['last_seen'] < 2.0: # Keep for 2 seconds
                if tid not in new_tracks:
                    new_tracks[tid] = tdata

        self.tracks = new_tracks
        return {tid: tdata['avg_speed'] for tid, tdata in new_tracks.items()}

def get_tracker():
    return AdvancedTracker()

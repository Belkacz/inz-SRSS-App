from typing import List, Tuple
from dataclasses import dataclass
import threading
import time
import numpy as np
import cv2
import websocket
from cardModule import CardMonitor
import tensorflow

@dataclass
class Box:
    x1: int
    y1: int
    x2: int
    y2: int
    conf: float

PERSON_COLORS = [
    (0, 255, 0),   # zielony – osoba 1
    (0, 0, 255),   # czerwony – osoba 2
    (255, 0, 0)    # niebieski – osoba 3
]

class FrameAnalyser:
    def __init__(self):
        self.max_people = 3
        self.confidence_threshold = 0.5
        model_base_dir = "tensorflow/ssd_mobilenet_v1_coco_2018_01_28/saved_model"

        try:
            model = tensorflow.saved_model.load(model_base_dir)
            self.detection_function = model.signatures['serving_default']
            print("[FrameAnalyser] ✓ Model TensorFlow SavedModel załadowany")
        except Exception as e:
            print(f"[FrameAnalyser] ✗ Błąd ładowania SavedModel: {e}")
            raise

    def FindPeople(self, frame) -> Tuple[int, List[Box]]:
        h, w = frame.shape[:2]
        input_tensor = tensorflow.convert_to_tensor(frame)
        input_tensor = input_tensor[tensorflow.newaxis, ...]  # dodaj wymiar batch

        detections = self.detection_function(input_tensor)

        # Wyciągnij wyniki
        boxes = detections['detection_boxes'][0].numpy()       # [num,4]
        scores = detections['detection_scores'][0].numpy()     # [num]
        classes = detections['detection_classes'][0].numpy()   # [num]

        results = []
        for box, score, class_id in zip(boxes, scores, classes):
            if score < self.confidence_threshold:
                continue
            if int(class_id) != 1:  # COCO class 1 = person
                continue
            ymin, xmin, ymax, xmax = box
            x1 = int(xmin * w)
            y1 = int(ymin * h)
            x2 = int(xmax * w)
            y2 = int(ymax * h)
            results.append(Box(x1, y1, x2, y2, score))

        # Tylko max_people najlepsze
        results = sorted(results, key=lambda b: b.conf, reverse=True)[:self.max_people]
        return len(results), results

    def erase_person(self, img, pt1, pt2):
        x1, y1 = pt1
        x2, y2 = pt2
        
        h, w = img.shape[:2]
        width = x2 - x1
        height = y2 - y1
        
        # MARGINES - 20%
        margin_x = int(0.2 * width)
        margin_y = int(0.2 * height)
        
        x1_new = max(0, x1 - margin_x)
        x2_new = min(w, x2 + margin_x)
        y1_new = max(0, y1 - margin_y)
        y2_new = min(h, y2 + margin_y)
        
        # Czarny prostokąt
        cv2.rectangle(img, (x1_new, y1_new), (x2_new, y2_new), (0, 0, 0), -1)
        return img

    def DrawBox(self, frame, boxes: List[Box], people_count):
        line_people_size = 2
        line_conf_size = 1
        drawed_frame = frame.copy()
        
        if people_count > 0:
            for idx, box in enumerate(boxes):
                # Wybierz kolor dla danej osoby
                color = PERSON_COLORS[idx] if idx < len(PERSON_COLORS) else (0, 255, 0)
                
                # Narysuj prostokąt
                cv2.rectangle(drawed_frame, (box.x1, box.y1), (box.x2, box.y2), color, 2)
                
                # Dodaj tekst z pewnością
                label = f"Person {idx+1}: {box.conf:.2f}"
                cv2.putText(drawed_frame, label, (box.x1, box.y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, line_conf_size)

        # Licznik osób
        cv2.putText(drawed_frame, f"Ludzi: {people_count}",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), line_people_size)
        
        return drawed_frame


class MotionDetector:
    def __init__(self, threshold=25, min_area=2000):
        self.threshold = 20
        self.min_area = min_area
        self.dead_zone = 30
        self.gaus_blur = 21

    def detectMotion(self, frame, prev_frame) -> bool:
        if frame.shape != prev_frame.shape:
            prev_frame = cv2.resize(prev_frame, (frame.shape[1], frame.shape[0]))

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (self.gaus_blur, self.gaus_blur), 0)

        prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
        prev_gray = cv2.GaussianBlur(prev_gray, (self.gaus_blur, self.gaus_blur), 0)

        frame_delta = cv2.absdiff(prev_gray, gray)
        _, thresh = cv2.threshold(frame_delta, self.threshold, 255, cv2.THRESH_BINARY)
        thresh = cv2.dilate(thresh, None, iterations=2)
        # cv2.imwrite("thresh.jpg", thresh)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        motion_detected = False
        for contour in contours:
            if cv2.contourArea(contour) > self.min_area:
                motion_detected = True
                break
        
        return motion_detected


class CAMMonitor:
    def __init__(self, ws_url: str, card_monitor: CardMonitor, 
                 detect_motion=True, find_people=True) -> None:
        self.ws_url = ws_url
        self.cam_connected = False
        self.card_monitor = card_monitor
        self.thread = threading.Thread(target=self._ws_listener, daemon=True)
        self.active = True
        self.prev_frame = None
        self.last_frame = None
        self.stremed_frame = None
        self.placeholder_frame = cv2.imread("stand_by.jpg")
        self.find_people = find_people
        self.detect_motion = detect_motion
        self.frame_analyser = FrameAnalyser()
        self.motion_detector = MotionDetector()
        
        self.motion_detected = False
        self.motion_saftey = False
        self.frames_with_movement = 0
        self.people_count = 0
        self.frame_counter = 0
        self.detection_boxes = []
        
        self.analyze_interval = 10  # Co ile klatek analizować
        self.stream_delay = 1/20  # FPS streamu
        
        print(f"[CAMMonitor] Inicjalizacja: analyze_interval={self.analyze_interval}", flush=True)

    def startThread(self):
        self.thread.start()

    def _ws_listener(self):
        print("[DEBUG] Wątek ws_listener wystartował!", flush=True)
        
        while self.active:
            try:
                ws = websocket.WebSocket()
                ws.connect(self.ws_url)
                self.cam_connected = True
                print(f"[CAMMonitor] ✓ Połączono z {self.ws_url}", flush=True)
                
                while self.active:
                    msg = ws.recv()
                    if not msg:
                        continue

                    if isinstance(msg, bytes):
                        nparr = np.frombuffer(msg, np.uint8)
                        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                        
                        if frame is not None:
                            self.frame_counter += 1
                            if self.frame_counter >= 60:
                                self.frame_counter = 0
                            
                            if self.detect_motion and self.prev_frame is not None:
                                self.motion_detected = self.motion_detector.detectMotion(
                                    frame, self.prev_frame)
                                if self.motion_detected:
                                    self.motion_saftey = True
                            self.prev_frame = frame

                            # Sprawdź czy ktoś jest
                            if not self.card_monitor.human_in:
                                self.people_count = 0
                                self.detection_boxes = []
                                self.stremed_frame = self.frame_analyser.DrawBox(frame, [], 0)
                                continue

                            if self.find_people and self.frame_counter % self.analyze_interval == 0:
                                self.people_count, self.detection_boxes = self.frame_analyser.FindPeople(frame)
                            
                            
                            self.stremed_frame = self.frame_analyser.DrawBox(
                                frame, self.detection_boxes, self.people_count
                            )
                        else:
                            print("[CAMMonitor] Błąd dekodowania klatki", flush=True)
                            self.stremed_frame = self.placeholder_frame.copy()

            except Exception as error:
                self.cam_connected = False
                print(f"[CAMMonitor] BŁĄD: {error}", flush=True)
                import traceback
                traceback.print_exc()
                self.stremed_frame = self.placeholder_frame.copy()
                time.sleep(5)

    def setSteamFramerate(self, fps: int):
        if fps < 60 and fps > 1:
            self.stream_delay = 1 / fps
            return True
        else:
            self.stream_delay = 0.033
            return False

    def generateFrames(self):
        """Generator dla Flask MJPEG stream"""
        while True:
            if self.stremed_frame is None:
                time.sleep(0.1)
                continue

            ret, buffer = cv2.imencode('.jpg', self.stremed_frame, 
                                     [cv2.IMWRITE_JPEG_QUALITY, 80])
            if not ret:
                time.sleep(0.1)
                continue

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            
            time.sleep(self.stream_delay)
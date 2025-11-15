from typing import List, Dict, Tuple, Any 
from dataclasses import dataclass
import threading
import queue
import time
from typing import Tuple, Dict, Any
from matplotlib.pyplot import box
import numpy as np
import cv2
import websocket
from flask import Flask, Response
# from ultralytics import YOLO
# import cv2
import mediapipe as mp

from cardModule import CardMonitor

@dataclass
class Box:
    x1: int
    y1: int
    x2: int
    y2: int
    conf: float

class FrameAnaylser:
    # def __init__(self) -> None:
        # self.hog = cv2.HOGDescriptor()
        # self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
        # self.mp_pose = mp.solutions.pose
        # self.pose = self.mp_pose.Pose(
        #     static_image_mode=False,
        #     model_complexity=0,  # 0=lite, 1=full, 2=heavy
        #     min_detection_confidence=0.5
        # )
            
    def DrawBox(self, frame, boxes: List[Box], people_count):
        line_poeple_size = 2
        line_conf_size = 1
        drawed_frame = frame.copy()
        if(people_count > 0):
            for idx, box in enumerate(boxes):
                cv2.rectangle(drawed_frame, (box.x1, box.y1), (box.x2, box.y2), (0, 255, 0), 1)
                cv2.putText(drawed_frame, f"conf: {box.conf:.2f}", (box.x1-10, box.y1-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), line_conf_size)
            # cv2.putText(drawed_frame, f"conf: {box.conf:.2f}", (10, 50),
            #         cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), line_conf_size)
        cv2.putText(drawed_frame, f"Ludzi: {people_count}",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), line_poeple_size)
        # cv2.putText(drawed_frame, f"conf: {0.00}", (10, 50),
        #             cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), line_conf_size)
        return drawed_frame
    
        # def FindPeople(self, frame) -> Tuple[int, List[Box]]:
        #     # MediaPipe używa RGB
        #     rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        #     results = self.pose.process(rgb_frame)
            
        #     if results.pose_landmarks:
        #         # Znajdź bounding box z landmarks
        #         h, w = frame.shape[:2]
        #         landmarks = results.pose_landmarks.landmark
                
        #         x_coords = [lm.x * w for lm in landmarks]
        #         y_coords = [lm.y * h for lm in landmarks]
                
        #         x1, y1 = int(min(x_coords)), int(min(y_coords))
        #         x2, y2 = int(max(x_coords)), int(max(y_coords))
                
        #         box = Box(x1, y1, x2, y2, 0.9)
        #         return 1, [box]
            
        #     return 0, []
        
        # def FindPeople(self, frame) -> Tuple[int, List[Box]]:
        #     try:
        #         # Opcjonalnie zmniejsz rozdzielczość dla szybkości
        #         # frame = cv2.resize(frame, (640, 480))
                
        #         (rects, weights) = self.hog.detectMultiScale(
        #             frame,
        #             winStride=(8, 8),
        #             padding=(4, 4),
        #             scale=1.05,
        #             useMeanshiftGrouping=True
        #         )
                
        #         boxes_data = []
        #         for i, (x, y, w, h) in enumerate(rects):
        #             # Filtruj słabe detekcje
        #             if weights[i] > 0.2:
        #                 box = Box(x, y, x + w, y + h, float(weights[i]))
        #                 boxes_data.append(box)
                
        #         return len(boxes_data), boxes_data
                
        #     except Exception as e:
        #         print(f"[FrameAnalyser] Błąd detekcji: {e}", flush=True)
        #         return 0, []

        # def FindPeople(self, frame) -> Tuple[Any, Dict[str, Any]]:
        #     results = self.model(frame[..., ::-1], imgsz=640, conf=0.25, classes=[0], verbose=False)
        #     detections = results[0].boxes

        #     people_count = len(detections)
        #     boxes_data = []
        #     for detection in detections:
        #         box = Box(0, 0, 0, 0, 0.00)
        #         box.x1, box.y1, box.x2, box.y1 = map(int, detection.xyxy[0])
                
        #         box.conf = float(detection.conf[0])
        #         boxes_data.append(box)

        #     # ret, buffer = cv2.imencode('.jpg', analysed_frame)
        #     # if ret:
        #     #     with open("test1.jpg", "wb") as file:
        #     #         file.write(buffer.tobytes())
        #     return people_count, boxes_data
        
class MotionDetector:
    def __init__(self, threshold=25, min_area=5000):
        self.threshold = threshold
        self.min_area = min_area
        self.dead_zone = 30

    def detectMotion(self, frame, prev_frame):
        # Usprawdzenie rozmiarów obu klatek
        if frame.shape != prev_frame.shape:
            prev_frame = cv2.resize(prev_frame, (frame.shape[1], frame.shape[0]))

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
        prev_gray = cv2.GaussianBlur(prev_gray, (21, 21), 0)

        # różnica miedzy klatkami
        frame_delta = cv2.absdiff(prev_gray, gray)
        _, thresh = cv2.threshold(frame_delta, self.threshold, 255, cv2.THRESH_BINARY)
        thresh = cv2.dilate(thresh, None, iterations=2)

        # zznajdź ruch
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        motion_detected = False
        for contour in contours:
            if cv2.contourArea(contour) > self.min_area:
                motion_detected = True
                self.dead_zone = 15
                # (x, y, w, h) = cv2.boundingRect(contour)
                # cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 1)
                # ret, buffer = cv2.imencode('.jpg', frame)
                # if ret:
                    # with open("test2.jpg", "wb") as file:
                        # file.write(buffer.tobytes())
            else:
                if self.dead_zone > 0:
                    motion_detected = True
                    self.dead_zone -= 1
        return motion_detected


# frame_queue = queue.Queue(maxsize=1)  # kolejka 1-elementowa

class CAMMonitor:
    def __init__(self, ws_url: str, card_monitor: CardMonitor, detect_motion=True, find_people=True) -> None:
        self.ws_url = ws_url
        self.card_monitor = card_monitor
        self.thread = threading.Thread(target=self._ws_listener, daemon=True)
        self.prev_frame = None
        self.last_frame = None
        self.active = True
        self.find_people = find_people
        self.detect_motion = detect_motion
        self.frame_analyser = FrameAnaylser()
        self.motion_detector = MotionDetector()
        self.stremed_frame = None
        self.motion_detected = False
        self.people_count = 0
        self.frame_counter = 0
        self.anylyze_interval = 5
        self.detection_boxes = []
        placeholder_path = "stand_by.jpg"
        self.placeholder_frame = cv2.imread(placeholder_path)
        self.anylyze_interval = 10

    def startThread(self):
        self.thread.start()
    def _ws_listener(self):
        print("[DEBUG] Wątek ws_listener wystartował!", flush=True)
        while self.active:
            try:
                ws = websocket.WebSocket()
                ws.connect(self.ws_url)
                print(f"[CAMMonitor] Połączono z {self.ws_url}")
                while self.active:
                    msg = ws.recv()
                    if not msg:
                        continue

                    if isinstance(msg, bytes):
                        with open("test.jpg", "wb") as file:
                            file.write(msg)
                        nparr = np.frombuffer(msg, np.uint8)
                        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                        if frame is not None:
                            if self.last_frame is not None:
                                self.prev_frame = self.last_frame
                            self.last_frame = frame
                            if self.card_monitor.human_in and self.prev_frame is not None and self.find_people:
                                self.motion_detected = self.motion_detector.detectMotion(self.last_frame, self.prev_frame)
                                # if self.frame_counter % self.anylyze_interval == 0:
                                    # self.people_count, self.detection_boxes, = self.frame_analyser.FindPeople(frame)

                            if (self.people_count > 0 and len(self.detection_boxes) > 0):
                                self.stremed_frame = self.frame_analyser.DrawBox(frame, self.detection_boxes, self.people_count)
                            else:
                                self.stremed_frame = self.frame_analyser.DrawBox(frame, [], 0)
                            self.frame_counter += 1
                            if self.frame_counter > 30:
                                self.frame_counter = 0
                            if self.card_monitor.human_in == False:
                                self.people_count = 0
                        else:
                            self.stremed_frame = self.placeholder_frame.copy()
                            print("[CAMMonitor] Nie udało się zdekodować klatki")
                    else:
                        self.stremed_frame = self.placeholder_frame.copy()
                        print(f"[CAMMonitor] [RAW MSG] {msg}")

            except Exception as exeption:
                print(f"[CAMMonitor] [BŁĄD] {exeption}, ponawiam połączenie za 5s...")
                self.stremed_frame = self.placeholder_frame.copy()
                time.sleep(5)

    def get_frame(self):
        return self.last_frame
    
    def generate_frames(self):
        frame_count = 0
        no_frame_count = 0
        
        while True:
            frame_to_stream = None
            
            # with self.frame_lock:
            # if self.stremed_frame is not None:
            #     frame_to_stream = self.stremed_frame.copy()
            #     no_frame_count = 0
            # else:
            #     no_frame_count += 1
            #     # Po 10 próbach (1 sekunda) użyj placeholder
            #     if no_frame_count > 10:
            #         frame_to_stream = self.placeholder_frame.copy()
            
            # Jeśli nadal nie ma klatki, czekaj krótko
            if self.stremed_frame is None:
                time.sleep(0.1)
                continue

            # # Kodowanie do JPEG
            # ret, buffer = cv2.imencode('.jpg', frame_to_stream, 
            #                            [cv2.IMWRITE_JPEG_QUALITY, 80])
            ret, buffer = cv2.imencode('.jpg', self.stremed_frame, 
                                       [cv2.IMWRITE_JPEG_QUALITY, 80])
            if not ret:
                print("[CAMMonitor] Błąd kodowania klatki")
                time.sleep(0.1)
                continue

            frame_count += 1
            if frame_count % 100 == 0:
                print(f"[CAMMonitor] Wysłano {frame_count} klatek")

            # Zwróć klatkę w formacie MJPEG
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            
            # Opcjonalne: limit FPS (30 fps = ~33ms)
            time.sleep(0.033)
    
    # def generate_frames(self):
    #     while True:
    #         if self.stremed_frame is None:
    #             time.sleep(0.1)
    #             continue

    #         ret, buffer = cv2.imencode('.jpg', self.stream_frame)
    #         if not ret:
    #             continue

    #         yield (b'--frame\r\n'
    #                b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

    # def generate_frames():
    #     while True:
    #         if not frame_queue.empty():
    #             frame = frame_queue.get()
    #             # Kodowanie do JPEG
    #             ret, buffer = cv2.imencode('.jpg', frame)
    #             if not ret:
    #                 continue
    #             frame_bytes = buffer.tobytes()
    #             # Strumieniowanie MJPEG
    #             yield (b'--frame\r\n'
    #                 b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

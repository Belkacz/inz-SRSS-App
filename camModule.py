from ast import Dict, Tuple
import threading
import queue
import time
from typing import Tuple, Dict, Any
import numpy as np
import cv2
import websocket
from flask import Flask, Response
from ultralytics import YOLO
import cv2

from cardModule import CardMonitor

class FrameAnaylser:
        def __init__(self) -> None:
            self.model = YOLO('yolov8n.pt')

        def FindPeople(self, frame) -> Tuple[Any, Dict[str, Any]]:
            results = self.model(frame[..., ::-1], imgsz=640, conf=0.35, classes=[0], verbose=False)  # tylko "person"
            detections = results[0].boxes

            people_count = len(detections)
            analysed_frame = frame.copy()
            boxes_data = []

            for box in detections:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                boxes_data.append({
                    'bbox': [x1, y1, x2, y2],
                    'confidence': conf
                })
                cv2.rectangle(analysed_frame, (x1, y1), (x2, y2), (0, 255, 0), 1)
                cv2.putText(analysed_frame, f"{conf:.2f}", (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

            cv2.putText(analysed_frame, f"Ludzi: {people_count}",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 1)
            ret, buffer = cv2.imencode('.jpg', analysed_frame)
            if ret:
                with open("test1.jpg", "wb") as file:
                    file.write(buffer.tobytes())
            # info = {
            #     'people_count': people_count,
            #     'detections': boxes_data
            # }
            return analysed_frame, people_count
        
class MotionDetector:
    def __init__(self, threshold=25, min_area=5000):
        self.threshold = threshold
        self.min_area = min_area
        self.dead_zone = 30

    def detectMotion(self, frame, prev_frame):
        # Upewnij się, że obie klatki mają ten sam rozmiar
        if frame.shape != prev_frame.shape:
            prev_frame = cv2.resize(prev_frame, (frame.shape[1], frame.shape[0]))

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
        prev_gray = cv2.GaussianBlur(prev_gray, (21, 21), 0)

        # różnica między bieżącą a poprzednią klatką
        frame_delta = cv2.absdiff(prev_gray, gray)
        _, thresh = cv2.threshold(frame_delta, self.threshold, 255, cv2.THRESH_BINARY)
        thresh = cv2.dilate(thresh, None, iterations=2)

        # znajdź kontury ruchu
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        motion_detected = False
        for contour in contours:
            if cv2.contourArea(contour) > self.min_area:
                motion_detected = True
                self.dead_zone = 15
                (x, y, w, h) = cv2.boundingRect(contour)
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 1)
                ret, buffer = cv2.imencode('.jpg', frame)
                if ret:
                    with open("test2.jpg", "wb") as file:
                        file.write(buffer.tobytes())
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
        self.anylase_frame = FrameAnaylser()
        self.motion_detector = MotionDetector()
        self.stremed_frame = None
        self.motion_detected = False
        self.people_detected = 0

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
                            analysed_frame = None
                            if self.card_monitor.human_in and self.prev_frame is not None and self.find_people:
                                self.motion_detected = self.motion_detector.detectMotion(self.last_frame, self.prev_frame)
                                analysed_frame, self.people_detected = self.anylase_frame.FindPeople(frame)
                            if analysed_frame is not None:
                                self.stremed_frame = analysed_frame
                            else:
                                self.stremed_frame = frame
                        else:
                            self.stremed_frame = None
                            print("[CAMMonitor] Nie udało się zdekodować klatki")
                    else:
                        self.stremed_frame = None
                        print(f"[CAMMonitor] [RAW MSG] {msg}")

            except Exception as exeption:
                print(f"[CAMMonitor] [BŁĄD] {exeption}, ponawiam połączenie za 5s...")
                self.stremed_frame = None
                time.sleep(5)

    def get_frame(self):
        return self.last_frame
    
    def generate_frames(self):
        frame_count = 0
        no_frame_count = 0
        
        while True:
            frame_to_stream = None
            
            # with self.frame_lock:
            if self.stremed_frame is not None:
                frame_to_stream = self.stremed_frame.copy()
                no_frame_count = 0
            else:
                no_frame_count += 1
                # Po 10 próbach (1 sekunda) użyj placeholder
                if no_frame_count > 10:
                    frame_to_stream = self.placeholder_frame.copy()
            
            # Jeśli nadal nie ma klatki, czekaj krótko
            if frame_to_stream is None:
                time.sleep(0.1)
                continue

            # Kodowanie do JPEG
            ret, buffer = cv2.imencode('.jpg', frame_to_stream, 
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

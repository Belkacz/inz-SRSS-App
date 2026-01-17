from datetime import datetime
import json
from typing import List, Tuple
from dataclasses import dataclass
import threading
import time
import numpy as np
import cv2
import websocket
from cardModule import CardMonitor

class CAMMonitor:
    def __init__(self, ws_url: str) -> None:
        self.ws_url = ws_url
        self.cam_connected = False
        self.thread = threading.Thread(target=self._ws_listener, daemon=True)
        self.active = True
        self.stremed_frame = None
        self.placeholder_frame = cv2.imread("stand_by.jpg")
        
        self.motion_detected = False
        self.motion_saftey = False
        self.last_motion_time = None
        self.people_count = 0
        self.frame_counter = 0
        self.json_counter = 0
        self.no_frame_counter = 0
        self.detection_boxes = []
        self.stream_delay = 1/15  # FPS streamu

    def startThread(self):
        self.thread.start()
        
    def _handle_motion_json(self, json_str):
        try:
            data = json.loads(json_str)
            motion = data.get("motion", False)
            timestamp = data.get("timestamp", 0)
            
            self.motion_detected = motion
            if motion:
                self.last_motion_time = datetime.fromtimestamp(timestamp)
            
            self.json_counter += 1
            return motion
            
        except json.JSONDecodeError as jsonError:
            print(f"[CAMMonitor] Błąd parsowania JSON: {jsonError}", flush=True)
        except Exception as error:
            print(f"[CAMMonitor] Błąd obsługi motion JSON: {error}", flush=True)
    # Obsługa klatki JPEG
    def _handle_frame(self, frame_data):
        try:
            nparr = np.frombuffer(frame_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is not None:
                self.last_frame = frame
                self.frame_counter += 1
        except Exception as error:
            print(f"[CAMMonitor] Błąd dekodowania klatki: {error}", flush=True)

    def _ws_listener(self):
        print("[DEBUG] Wątek ws_listener wystartował!", flush=True)
        
        while self.active:
            try:
                ws = websocket.WebSocket()
                ws.connect(self.ws_url)
                self.cam_connected = True
                print(f"[CAMMonitor] ✓ Połączono z {self.ws_url}", flush=True)
                
                while self.active:
                    try:
                        msg = ws.recv()
                        if not msg:
                            time.sleep(0.1)
                            continue
                        if isinstance(msg, bytes):
                            nparr = np.frombuffer(msg, np.uint8)
                            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                            if frame is not None:
                                self.no_frame_counter = 0
                                self.frame_counter += 1
                                if self.frame_counter >= 60:
                                    self.frame_counter = 0

                                self.stremed_frame = frame
                            else:
                                self.no_frame_counter += 1
                                print("[CAMMonitor] Błąd dekodowania klatki", flush=True)
                                if self.no_frame_counter > 30:
                                    self.stremed_frame = self.placeholder_frame.copy()
                                    if self.no_frame_counter > 99 : self.no_frame_counter = 31
                        elif isinstance(msg, str):
                            # To jest JSON z informacją o ruchu
                            self.motion_detected = self._handle_motion_json(msg)
                            if(self.motion_detected):
                                self.motion_saftey = True
                    except websocket.WebSocketTimeoutException:
                        time.sleep(0.1)
                        continue  # Timeout jest OK
            except Exception as error:
                self.cam_connected = False
                print(f"[CAMMonitor] BŁĄD: {error}", flush=True)
                import traceback
                traceback.print_exc()
                self.stremed_frame = self.placeholder_frame.copy()
                time.sleep(5)
# Generator dla Flask MJPEG stream
    def generateFrames(self):
        while True:
            if self.stremed_frame is None:
                time.sleep(0.1)
                continue

            ret, buffer = cv2.imencode('.jpg', self.stremed_frame, 
                                     [cv2.IMWRITE_JPEG_QUALITY, 70])
            if not ret:
                time.sleep(0.1)
                continue

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            
            time.sleep(self.stream_delay)
from datetime import datetime
import json
import threading
import time
import websocket

class CAMMonitor:
    def __init__(self, ws_url: str) -> None:
        self.ws_url = ws_url
        self.cam_connected = False
        self.thread = threading.Thread(target=self._ws_listener, daemon=True)
        self.active = True
        
        # Zakoduj placeholder raz przy starcie
        try:
            with open("stand_by.jpg", "rb") as placeholder_file:
                self.placeholder_jpeg = placeholder_file.read()
            print("[CAMMonitor] Wczytano placeholder", flush=True)
        except FileNotFoundError:
            print("[CAMMonitor] Nie znaleziono stand_by.jpg", flush=True)
            self.placeholder_jpeg = 0
        except Exception as e:
            print(f"[CAMMonitor] Błąd wczytywania placeholder: {e}", flush=True)
            self.placeholder_jpeg = 0
        
        # Startuj z placeholder
        self.stremed_frame = self.placeholder_jpeg
        
        self.motion_detected = False
        self.motion_saftey = False
        self.last_motion_time = None
        self.no_frame_counter = 0
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
            return motion
        except json.JSONDecodeError as jsonError:
            print(f"[CAMMonitor] Błąd parsowania JSON: {jsonError}", flush=True)
            return None
        except Exception as error:
            print(f"[CAMMonitor] Błąd obsługi motion JSON: {error}", flush=True)
            return None

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
                            # kopiowanie klatki jpg
                            if len(msg) > 2 and msg[:2] == bytes([0xff, 0xd8]):
                                self.no_frame_counter = 0
                                self.stremed_frame = msg
                            else:
                                self.no_frame_counter += 1
                                print("[CAMMonitor] Błędny format klatki", flush=True)
                                if self.no_frame_counter > 5:
                                    self.stremed_frame = self.placeholder_jpeg
                                    if self.no_frame_counter > 99:
                                        self.no_frame_counter = 31
                                        
                        elif isinstance(msg, str):
                            # JSON z informacją o ruchu
                            self.motion_detected = self._handle_motion_json(msg)
                            if self.motion_detected:
                                self.motion_saftey = True
                                
                    except websocket.WebSocketTimeoutException:
                        time.sleep(0.1)
                        continue
                        
            except Exception as error:
                self.cam_connected = False
                print(f"[CAMMonitor] BŁĄD: {error}", flush=True)
                import traceback
                traceback.print_exc()
                self.stremed_frame = self.placeholder_jpeg
                time.sleep(5)
    # Generator dla Flask MJPEG stream
    def generateFrames(self):
        while True:
            if self.stremed_frame is None or len(self.stremed_frame) == 0:
                time.sleep(0.1)
                continue
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + 
                   self.stremed_frame + 
                   b'\r\n')
            
            time.sleep(self.stream_delay)
from datetime import datetime
import json
import threading
import time
import websocket

class CAMMonitor:
    def __init__(self, ws_url: str, reconnect_delay: float = 5.0, empty_msg_delay: float = 0.1, ws_timeout_delay: float = 0.1,) -> None:
        self.ws_url = ws_url
        self.cam_connected = False
        self.thread = threading.Thread(target=self._ws_listener, daemon=True)
        self.active = True
        
        # Timeouty
        self.reconnect_delay = reconnect_delay
        self.empty_msg_delay = empty_msg_delay
        self.ws_timeout_delay = ws_timeout_delay
        self.stream_delay = 1/5 # podział 1 sekunda / 5 fps
        
        # Zakoduj placeholder raz przy starcie
        try:
            with open("stand_by.jpg", "rb") as placeholder_file:
                self.placeholder_jpeg = placeholder_file.read()
            print("[CAMMonitor] Wczytano placeholder", flush=True)
        except Exception as error:
            print(f"[CAMMonitor] Błąd wczytywania placeholder: {error}", flush=True)
            self.placeholder_jpeg = None
        
        # Startuj z placeholder
        self.stremed_frame = self.placeholder_jpeg
        
        self.motion_detected = False
        self.motion_saftey = False
        self.last_motion_time = None
        self.no_frame_counter = 0

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
        except Exception as error:
            print(f"[CAMMonitor] Błąd obsługi motion JSON: {error}", flush=True)
            return None

    def _ws_listener(self):
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
                            time.sleep(self.empty_msg_delay)
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
                        time.sleep(self.ws_timeout_delay)
                        continue
                        
            except Exception as error:
                self.cam_connected = False
                print(f"[CAMMonitor] Błąd: {error}, ponawiam połączenie za {self.reconnect_delay}s...")
                import traceback
                traceback.print_exc()
                self.stremed_frame = self.placeholder_jpeg
                time.sleep(self.reconnect_delay)
    # Generator dla Flask MJPEG stream
    def generateFrames(self):
        while True:
            if self.stremed_frame is None or len(self.stremed_frame) == 0:
                time.sleep(self.empty_msg_delay)
                continue
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + 
                   self.stremed_frame + 
                   b'\r\n')
            
            time.sleep(self.stream_delay)
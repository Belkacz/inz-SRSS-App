from http.client import SWITCHING_PROTOCOLS
from numbers import Number
import threading
import websocket
import json
import time

class PIRMonitor:
    def __init__(self, ws_url: str) -> None:
        self.ws_url = ws_url
        self.last_pir_data = {}
        self.active = True
        # self.lock = threading.Lock()
        self.thread = threading.Thread(target=self._ws_listener, daemon=True)
        self.pir26Counter = 0
        self.pir16Counter = 0

    def startThread(self):
        self.thread.start()

    def get_data(self):
        # with self.lock:
        return dict(self.last_pir_data)
    def getPirCounter(self, pir: Number) -> Number:
        match pir:
            case 26:
                return self.pir26Counter
            case 16:
                return self.pir16Counter
            case _:
                return 0

    def restCounters(self):
        self.pir26Counter = 0
        self.pir16Counter = 0

    def _ws_listener(self):
        print("[DEBUG] Wątek ws_listener wystartował!", flush=True)
        while self.active:
            try:
                ws = websocket.WebSocket()
                ws.connect(self.ws_url)
                print(f"[INFO] Połączono z {self.ws_url}")
                while self.active:
                    msg = ws.recv()
                    if msg:
                        try:
                            data = json.loads(msg)
                            # with self.lock:

                            self.last_pir_data = data
                            self.pir26Counter = self.pir26Counter + data.get('pir26RisingCounter')
                            self.pir16Counter = self.pir16Counter + data.get('pir26RisingCounter')
                            if self.pir26Counter > 99:
                                self.pir26Counter = 1
                            if self.pir16Counter > 99:
                                self.pir16Counter = 1
                            print(f"[dane PIR] {data}")
                        except Exception:
                            print(f"[RAW] {msg}")
            except Exception as e:
                print(f"[BŁĄD] {e}, ponawiam połączenie za 5s...")
                time.sleep(5)

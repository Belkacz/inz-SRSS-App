from http.client import SWITCHING_PROTOCOLS
from numbers import Number
import threading
import websocket
import json
import time

class PIRMonitor:
    def __init__(self, ws_url: str) -> None:
        self.ws_url = ws_url
        self.pir_connected = False
        self.active = True
        self.thread = threading.Thread(target=self._ws_listener, daemon=True)
        self.pir26Counter = 0
        self.pir16Counter = 0

    def startThread(self):
        self.thread.start()

    def getPirCounter(self, pir: Number) -> Number:
        match pir:
            case 26:
                return self.pir26Counter
            case 16:
                return self.pir16Counter
            case _:
                return 0

    # metoda do restowania wartości pir
    def restCounters(self):
        self.pir26Counter = 0
        self.pir16Counter = 0

    def _ws_listener(self):
        while self.active:
            try:
                ws = websocket.WebSocket()
                ws.connect(self.ws_url)
                self.pir_connected = True
                while self.active:
                    msg = ws.recv()
                    if msg:
                        try:
                            data = json.loads(msg)
                            self.pir26Counter = self.pir26Counter + data.get('pir26RisingCounter')
                            self.pir16Counter = self.pir16Counter + data.get('pir16RisingCounter')
                            # if self.pir26Counter > 99:
                            #     self.pir26Counter = 99
                            # if self.pir16Counter > 99:
                            #     self.pir16Counter = 99
                        except Exception as json_error:
                            print(f"[PIRMonitor] Bład dekodowania Json: {json_error}")
                    time.sleep(1)
            except Exception as error:
                self.pir_connected = False
                print(f"[PIRMonitor] Błąd : {error}, ponawiam połączenie za 5s...")
                time.sleep(5)

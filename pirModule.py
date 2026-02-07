from numbers import Number
import threading
import websocket
import json
import time

class PIRMonitor:
    def __init__(self, ws_url: str, reconnect_delay: float = 5.0, empty_msg_delay: float = 0.1, error_delay: float = 0.5) -> None:
        self.ws_url = ws_url
        self.pir_connected = False
        self.active = True
        
        # Timeouty
        self.reconnect_delay = reconnect_delay
        self.empty_msg_delay = empty_msg_delay
        self.error_delay = error_delay
        
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
    # metoda do resetowania wartości pir
    def resetCounters(self):
        self.pir26Counter = 0
        self.pir16Counter = 0

    def _ws_listener(self):
        while self.active:
            try:
                ws = websocket.WebSocket()
                ws.connect(self.ws_url)
                self.pir_connected = True
                print(f"[PIRMonitor] Połączono z {self.ws_url}", flush=True)
                
                while self.active:
                    msg = ws.recv()
                    if not msg:
                        time.sleep(self.empty_msg_delay)
                        continue
                    try:
                        data = json.loads(msg)
                        self.pir26Counter = self.pir26Counter + data.get('pir26RisingCounter')
                        self.pir16Counter = self.pir16Counter + data.get('pir16RisingCounter')
                        if self.pir26Counter > 999 : self.pir26Counter = 999
                        if self.pir16Counter > 999 : self.pir16Counter = 999
                    except Exception as error:
                        print(f"[PIRMonitor] Błąd przetwarzania: {error}", flush=True)
                        time.sleep(self.error_delay)
                        
            except Exception as error:
                self.pir_connected = False
                print(f"[PIRMonitor] Błąd: {error}, ponawiam połączenie za {self.reconnect_delay}s...", flush=True)
                time.sleep(self.reconnect_delay)
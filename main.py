from numbers import Number
from flask import Flask
from routes import register_routes
from pirModule import PIRMonitor
from camModule import CAMMonitor
from cardModule import CardMonitor, UserHandler
from shared import AlarmManager
from settings import settings
import threading
import time
# from dotenv import load_dotenv
import os


# load_dotenv()

# def monitor_pir():
#     last_pir26_counter = None
#     last_pir16_counter = None
#     last_activity_time = time.time()
#     print("[DEBUG] Wątek monitor_pir wystartował!", flush=True)
    
#     while True:
#         time.sleep(5)
#         pir_data = pir_monitor.get_data()

#         current_pir26 = pir_data.get('pir26RisingCounter')
#         current_pir16 = pir_data.get('pir16RisingCounter')
        
#         if current_pir26 is not None and current_pir16 is not None:
#             if (last_pir26_counter is not None and last_pir16_counter is not None):
#                 if current_pir26 != last_pir26_counter or current_pir16 != last_pir16_counter:
#                     print(f"[AKTYWNOŚĆ] PIR26: {last_pir26_counter}->{current_pir26}, PIR16: {last_pir16_counter}->{current_pir16}")
#                     last_activity_time = time.time()
#                     if alarm_manager.get_alarm():
#                         alarm_manager.set_alarm(False)
#                         print("[ALARM] Wyłączony - wykryto ruch!")
            
#             last_pir26_counter = current_pir26
#             last_pir16_counter = current_pir16

#             time_since_activity = time.time() - last_activity_time
#             if time_since_activity >= 60 and not alarm_manager.get_alarm():
#                 alarm_manager.set_alarm(True)
#                 print(f"[ALARM] Włączony! Brak aktywności przez {time_since_activity:.1f}s")

class AlertPir:
    def __init__(self, ws_url: str, pir_monitor:PIRMonitor, alarmManager:AlarmManager, checkInterval:Number = 60)->None:
        self.ws_url = ws_url
        self.pir_monitor = pir_monitor
        self.checkInterval = checkInterval
        self.working = True
        self.current_pir26 = None
        self.current_pir16 = None
        self.alarmManager = alarmManager
        self.thread = threading.Thread(target=self.startPirAlerts, daemon=True)
        self.lastCounterRestTime = time.time()

    def getPirCounter(self, pir: Number) -> Number:
        match pir:
            case 26:
                return self.current_pir26
            case 16:
                return self.current_pir16
            case _:
                return 0

    def startPirAlerts(self):
        while self.working:
            time.sleep(self.checkInterval)
            # pir_data = self.pir_monitor.get_data()

            self.current_pir26 = self.pir_monitor.getPirCounter(26)
            self.current_pir16 = self.pir_monitor.getPirCounter(16)
            if self.current_pir26 is not None or self.current_pir16 is not None:
                if self.current_pir26 > 0 or self.current_pir16 > 0:
                    self.alarmManager.setPirAlarm(False)
                else:
                    self.alarmManager.setPirAlarm(True)
                self.pir_monitor.restCounters()
                self.lastCounterRestTime = time.time()
            else:
                self.alarmManager.setPirAlarm(False)
                print("No pir data")
            print(f"self.current_pir26  = {self.current_pir26 },self.current_pir16 = {self.current_pir16} ")

    def startThread(self):
        self.thread.start()


def main():
    app = Flask(__name__)

    pir_monitor = PIRMonitor(settings.WS_SERVER_URL)
    alarm_manager = AlarmManager()
    alarm_pir = AlertPir(settings.WS_SERVER_URL, pir_monitor, alarm_manager, 30)
    user_handler = UserHandler(settings.DB_URL)
    card_monitor = CardMonitor(settings.WS_CARD_URL, user_handler)
    cam_monitor = CAMMonitor(settings.WS_CAMERA_URL, card_monitor)
    
    register_routes(app, pir_monitor, alarm_manager, alarm_pir, cam_monitor, card_monitor)

    pir_monitor.startThread()

    alarm_pir.startThread()
    
    card_monitor.startThread()
    
    cam_monitor.startThread()

    # --- Start Flask
    app.run(host='0.0.0.0', port=5000, use_reloader=False)
if __name__ == "__main__":
    main()


from numbers import Number
from flask import Flask
from routes import register_routes
from pirModule import PIRMonitor
from camModule import CAMMonitor
from cardModule import CardMonitor, UserHandler
from safetyMonitor import SafetyMonitor
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

# class AlertPir:
#     def __init__(self, ws_url: str, pir_monitor:PIRMonitor, alarmManager:AlarmManager, checkInterval:Number = 60)->None:
#         self.ws_url = ws_url
#         self.pir_monitor = pir_monitor
#         self.checkInterval = checkInterval
#         self.working = True
#         self.current_pir26 = None
#         self.current_pir16 = None
#         self.alarmManager = alarmManager
#         self.thread = threading.Thread(target=self.startPirAlerts, daemon=True)
#         self.lastCounterRestTime = time.time()

#     def getPirCounter(self, pir: Number) -> Number:
#         match pir:
#             case 26:
#                 return self.current_pir26
#             case 16:
#                 return self.current_pir16
#             case _:
#                 return 0

#     def startPirAlerts(self):
#         while self.working:
#             time.sleep(self.checkInterval)
#             # pir_data = self.pir_monitor.get_data()

#             self.current_pir26 = self.pir_monitor.getPirCounter(26)
#             self.current_pir16 = self.pir_monitor.getPirCounter(16)
#             if self.current_pir26 is not None or self.current_pir16 is not None:
#                 if self.current_pir26 > 0 or self.current_pir16 > 0:
#                     self.alarmManager.setPirAlarm(False)
#                 else:
#                     self.alarmManager.setPirAlarm(True)
#                 self.pir_monitor.restCounters()
#                 self.lastCounterRestTime = time.time()
#             else:
#                 self.alarmManager.setPirAlarm(False)
#                 print("No pir data")
#             print(f"self.current_pir26  = {self.current_pir26 },self.current_pir16 = {self.current_pir16} ")

#     def startThread(self):
#         self.thread.start()
        
# class SafetyMonitor:
#     def __init__(self, ws_url: str, pir_monitor:PIRMonitor, cam_monitor:CAMMonitor, card_monitor: CardMonitor,
#                  alarmManager:AlarmManager, pir_interval = 60, cam_interval = 60, alert_interval:Number = 60)->None:
#         self.ws_url = ws_url
#         self.pir_monitor = pir_monitor
#         self.cam_monitor = cam_monitor
#         self.card_monitor = card_monitor

#         self.alert_interval = alert_interval
#         self.pir_interval = pir_interval
#         self.cam_interval = cam_interval
        
#         self.working = True
#         self.current_pir26 = None
#         self.current_pir16 = None
#         self.alarmManager = alarmManager
        
#         self.last_pir_check = 0
#         self.last_cam_check = 0
#         self.last_alert_check = 0
        
#         self.pir_alarm = False
#         self.cam_alarm = False
#         self.people_in_danger = 0
        
#         self.danger = False
        
#         self.thread = threading.Thread(target=self.startAlerts, daemon=True)
#     def startThread(self):
#         self.thread.start()

#     def startAlerts(self):
#         while self.working:
#             iteration_time = time.time()
#             # pir_data = self.pir_monitor.get_data()
#             if iteration_time - self.last_pir_check >= self.pir_interval :
#                 self.current_pir26 = self.pir_monitor.getPirCounter(26)
#                 self.current_pir16 = self.pir_monitor.getPirCounter(16)
#                 if self.current_pir26 is not None or self.current_pir16 is not None:
#                     if self.current_pir26 > 0 or self.current_pir16 > 0:
#                         self.pir_alarm = False
#                     else:
#                         self.pir_alarm = True
#                     self.pir_monitor.restCounters()
#                 else:
#                     self.alarmManager.setPirAlarm(False)
#                     print("No pir data")
#                 print(f"self.current_pir26  = {self.current_pir26 },self.current_pir16 = {self.current_pir16} ")
#                 self.last_pir_check = iteration_time

#             if iteration_time - self.last_cam_check >= self.cam_interval:
#                 cam_motion = getattr(self.cam_monitor, "motion_detected", False)
#                 self.people_in_danger = getattr(self.cam_monitor, "people_count", 0)
#                 if(cam_motion):
#                     self.cam_alarm = False
#                 else:
#                     self.cam_alarm = True
#                 print(f"[SafetyMonitor] Camera: motion={cam_motion}, people={self.people_in_danger}")
#                 setattr(self.cam_monitor, "motion_detected", False)
#                 self.last_cam_check = iteration_time
                
#             if iteration_time - self.last_alert_check >= self.alert_interval:
#                 if self.cam_alarm and self.pir_alarm and getattr(self.card_monitor, "human_in", False):
#                     self.danger = True
#                 self.last_alert_check = iteration_time


def main():
    app = Flask(__name__)

    pir_monitor = PIRMonitor(settings.WS_SERVER_URL)
    # alarm_pir = AlertPir(settings.WS_SERVER_URL, pir_monitor, alarm_manager, 30)
    user_handler = UserHandler(settings.DB_URL)
    card_monitor = CardMonitor(settings.WS_CARD_URL, user_handler)
    cam_monitor = CAMMonitor(settings.WS_CAMERA_URL, card_monitor)
    
    safety_monitor = SafetyMonitor(pir_monitor, cam_monitor, card_monitor, 30, 30, 60)
    register_routes(app, pir_monitor, safety_monitor, cam_monitor, card_monitor)

    pir_monitor.startThread()

    card_monitor.startThread()

    cam_monitor.startThread()

    safety_monitor.startThread()

    # --- Start Flask
    app.run(host='0.0.0.0', port=5000, use_reloader=False)
if __name__ == "__main__":
    main()


import time
import threading

from camModule import CAMMonitor
from cardModule import CardMonitor
from pirModule import PIRMonitor

class SafetyMonitor:
    def __init__(self, pir_monitor:PIRMonitor, cam_monitor:CAMMonitor, card_monitor: CardMonitor,
                    pir_interval = 60, cam_interval = 60, alert_interval = 60)->None:
        self.pir_monitor = pir_monitor
        self.cam_monitor = cam_monitor
        self.card_monitor = card_monitor

        self.alert_interval = alert_interval
        self.pir_interval = pir_interval
        self.cam_interval = cam_interval
        
        self.working = True
        self.current_pir26 = None
        self.current_pir16 = None
        
        self.last_pir_check = time.time()
        self.last_cam_check = time.time()
        self.last_alert_check = time.time()
        
        self.pir_alarm = False
        self.cam_alarm = False
        self.people_in_danger = 0
        
        self.danger = False
        
        self.thread = threading.Thread(target=self.startAlerts, daemon=True)
    def startThread(self):
        self.thread.start()

    def startAlerts(self):
        while self.working:
            iteration_time = time.time()
            # pir_data = self.pir_monitor.get_data()
            if iteration_time - self.last_pir_check >= self.pir_interval :
                self.current_pir26 = self.pir_monitor.getPirCounter(26)
                self.current_pir16 = self.pir_monitor.getPirCounter(16)
                if self.current_pir26 is not None or self.current_pir16 is not None:
                    if self.current_pir26 > 0 or self.current_pir16 > 0:
                        self.pir_alarm = False
                    else:
                        self.pir_alarm = True
                    self.pir_monitor.restCounters()
                else:
                    self.pir_alarm = False
                    print("No pir data")
                print(f"self.current_pir26  = {self.current_pir26 },self.current_pir16 = {self.current_pir16} ")
                self.last_pir_check = iteration_time

            if iteration_time - self.last_cam_check >= self.cam_interval:
                cam_motion = self.cam_monitor.motion_saftey
                self.people_in_danger = self.cam_monitor.people_count
                if(cam_motion):
                    self.cam_alarm = False
                else:
                    self.cam_alarm = True
                print(f"[SafetyMonitor] Camera: motion={cam_motion}, people={self.people_in_danger}")
                setattr(self.cam_monitor, "motion_detected", False)
                self.last_cam_check = iteration_time
                
            if iteration_time - self.last_alert_check >= self.alert_interval:
                print(f"self.card_monitor.human_in =  {self.card_monitor.human_in}")
                if self.cam_alarm and self.pir_alarm and self.card_monitor.human_in:
                    self.danger = True
                    print("\n DANSGHUDJSHADHKAHDKAH DANGERRRRR \n")
                    print("\n DANSGHUDJSHADHKAHDKAH DANGERRRRR \n")
                    print("\n DANSGHUDJSHADHKAHDKAH DANGERRRRR \n")
                    print("\n DANSGHUDJSHADHKAHDKAH DANGERRRRR \n")
                self.last_alert_check = iteration_time
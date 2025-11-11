import threading

class AlarmManager:
    def __init__(self) -> None:
        self.PirAlarm = False
        # self.lock = threading.Lock()

    def setPirAlarm(self, value: bool) -> None:
        # with self.lock:
        self.PirAlarm = value

    def getPirAlarm(self) -> bool:
        # with self.lock:
        return self.PirAlarm

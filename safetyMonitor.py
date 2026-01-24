from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import time
import threading
import cv2
from camModule import CAMMonitor
from cardModule import CardMonitor
from pirModule import PIRMonitor
import smtplib
from settings import settings
from enum import Enum

class STATUS(Enum):
    OK = 0
    WARNING = 1
    ALARM = 2

"""
Args:
    users_in: lista użytkowników wewnątrz
    pir26: stan odczytu z czujnika pir26
    pir16: stan odczytu z czujnika pir16
    frame: klatka z kamery
"""
def sendAlertEmail(users_in: tuple[list], pir26, pir16, frame):
    
    users_in_danger = []
    for user in users_in:
        users_in_danger.append(
            f"  - {user.first_name} {user.second_name} (Karta: {user.card_number})"
        )
    
    users_list = "\n".join(users_in_danger) if users_in_danger else "  - Brak danych o użytkownikach"
    subject = "ALARM SAFETYMONITOR – BRAK OZNAK ŻYCIA, LUDZIE OBECNI W POMIESZCZENIU"
    body = (
        "WYKRYTO STAN ZAGROŻENIA DLA OSÓB W POMIESZCZENIU\n\n"
        "═══════════════════════════════════════════════════\n"
        "Człowiek jest w środku, ale nie wykryto ruchu\n"
        "Status czujników:\n"
        f"   • PIR26: {pir26} detekcji\n"
        f"   • PIR16: {pir16} detekcji\n"
        f"   • Kamera: Brak ruchu\n"
        f"   • Liczba osób zagrożonych: {len(users_in_danger)}\n\n"
        "OSOBY NARAŻONE NA NIEBEZPIECZEŃSTWO:\n"
        f"{users_list}\n\n"
        "═══════════════════════════════════════════════════\n"
        "  NATYCHMIAST SPRAWDŹ SYTUACJĘ!\n"
        f"Data zdarzenia: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        "Zobacz załączony obraz z kamery monitoringu.\n"
    )

    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = settings.EMAIL_HOST_USER
    msg['To'] = settings.RECIPIENT_EMAIL
    
    msg.attach(MIMEText(body, 'plain', 'utf-8'))
    
    if frame is not None:
        try:
            target_width = 854
            target_height = 480
            
            resized_frame = cv2.resize(frame, (target_width, target_height), interpolation=cv2.INTER_AREA)
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 85]
            _, img_encoded = cv2.imencode('.jpg', resized_frame, encode_param)
            img_bytes = img_encoded.tobytes()
            
            image_attachment = MIMEImage(img_bytes, name=f"alarm_{time.strftime('%Y%m%d_%H%M%S')}.jpg")
            image_attachment.add_header(
                'Content-Disposition', 
                'attachment', 
                filename=f"alarm_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
            )
            msg.attach(image_attachment)
            
            print(f"[SafetyMonitor] Dodano obrazek 854x480 ({len(img_bytes)//1024}KB) do maila", flush=True)
        except Exception as error:
            print(f"[SafetyMonitor] Błąd dodawania obrazka: {error}", flush=True)
    else:
        print("[SafetyMonitor] Brak klatki z kamery", flush=True)

    try:
        with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
            server.starttls()
            server.login(settings.EMAIL_HOST_USER, settings.EMAIL_PASS)
            server.send_message(msg)
            print("[SafetyMonitor] Wysłano maila alarmowego!", flush=True)
            return True
    except Exception as erorr:
        print(f"[SafetyMonitor] Błąd wysyłania maila: {erorr}", flush=True)
        return False

"""
Args:
    pir_monitor: instancja klasy monitora Pir
    cam_monitor: instancja klasy monitora kamery
    card_monitor: instancja klasy monitora kart
    warning_interval: jak często sprawdzać warunki osrzeżenia - zabarwiony ekran
    alert_interval: jak często sprawdzać warunki alarmu - wysyłka maila
"""
class SafetyMonitor:
    def __init__(self, pir_monitor: PIRMonitor, cam_monitor: CAMMonitor, card_monitor: CardMonitor,
                warning_interval=60, alert_interval=(60*5)) -> None:
        self.pir_monitor = pir_monitor
        self.cam_monitor = cam_monitor
        self.card_monitor = card_monitor
        
        self.warning_interval = warning_interval
        self.alert_interval = alert_interval
        self._main_interval = 10

        self.working = True

        # Dane z czujników (aktualizowane często)
        self.ui_pir26 = 0
        self.ui_pir16 = 0
        self.ui_cam_motion = False
        self.total_pir26 = 0
        self.total_pir16 = 0
        self.total_cam_motion = False
        
        # Czasy ostatnich sprawdzeń
        self.warning_time = None

        # Stan głównego zagrożenia (aktualizowany rzadko - dla maili)
        self.status = STATUS.OK
        self.main_alert_on = True
        self.email_sent = False
        self.ui_timestamp = time.time()

        self.thread = threading.Thread(target=self._startAlerts, daemon=True)

    # metoda rozpoczytnjąca wątek
    def startThread(self):
        self.thread.start()
        print("[SafetyMonitor] Wątek uruchomiony", flush=True)

    # metoda do resetu alarmów
    def resetData(self):
        self.main_alert_on = True 
        self.email_sent = False
        self.status = STATUS.OK
        self.warning_time = None
        self.total_pir26 = 0
        self.total_pir16 = 0
    
    def _collectSensorData(self):
        """
        PRYWATNA metoda - zbiera dane z modułów czujników.
        Wywoływana TYLKO przez wątek backendowy!
        Aktualizuje ZARÓWNO ui_* (dla UI) JAK I total_* (dla logiki alarmowej)
        """
        # Pobierz dane PIR (resetuje liczniki w PIRMonitor)
        pir26 = self.pir_monitor.getPirCounter(26)
        pir16 = self.pir_monitor.getPirCounter(16)
        pir26 = pir26 if pir26 is not None else 0
        pir16 = pir16 if pir16 is not None else 0
        # Pobierz dane kamery (NIE resetuj motion_saftey - to robi tylko reset)
        cam_motion = self.cam_monitor.motion_saftey
        self.ui_timestamp = time.time()
        self.ui_pir26 += pir26
        self.ui_pir16 += pir16
        self.total_pir26 += pir26
        self.total_pir16 += pir16
        if cam_motion:
            self.ui_cam_motion = True  # Raz True = zostaje True do resetu
            self.total_cam_motion = True

        self.pir_monitor.resetCounters()
        self.cam_monitor.motion_saftey = False

    def getSensorData(self):
        """
        Zwraca sensor data dla UI (thread-safe).
        RESETUJE ui_* po odczycie, ale NIE dotyka total_* (te są dla logiki alarmowej)
        """
        sensor_data = {
            "pir26": self.ui_pir26,
            "pir16": self.ui_pir16,
            "cam_motion": self.ui_cam_motion,
            "timestamp": self.ui_timestamp,
            "pir_alarm": self.ui_pir26 == 0 and self.ui_pir16 == 0,
        }
        self.ui_pir26 = 0
        self.ui_pir16 = 0
        self.ui_cam_motion = False
        return sensor_data


    def _startAlerts(self):
        """
        Główny moduł alarmowy
        """
        while self.working:
            iteration_time = time.time()
            # SPRAWDZANIE GŁÓWNEGO ALERTU
            if self.main_alert_on:
                self._collectSensorData()
                # warunek sprawdzajacy zagrożenie
                if self.total_cam_motion == False and self.total_pir26 == 0 and self.total_pir16 == 0 and self.card_monitor.human_in:
                    # warunek sprawdzajacy czy nie było zagrozenia
                    if self.warning_time is None and self.status == STATUS.OK:
                        self.warning_time = time.time()
                        # els if do sprawdzenia czasu od zagrożenia dla żółtego ekranu
                    elif self.warning_time is not None and iteration_time - self.warning_time > self.warning_interval:
                        self.status = STATUS.WARNING
                    # warunek dla czasu do alertu i czy w zagrożeniu już wysłaliśmy wiadomość
                    if not self.email_sent and self.warning_time is not None and iteration_time - self.warning_time > self.alert_interval:
                        self.status = STATUS.ALARM
                        # próba wysyłki maila
                        try:
                            if sendAlertEmail(
                                self.card_monitor.users_in,
                                self.total_pir26,
                                self.total_pir16,
                                self.cam_monitor.stremed_frame
                            ):
                                print("[SafetyMonitor] Mail wysłany pomyślnie", flush=True)
                                self.email_sent = True
                                self.main_alert_on = False
                            else:
                                print("[SafetyMonitor] Nie udało się wysłać maila", flush=True)
                        except Exception as error:
                            print(f"[SafetyMonitor] Wyjątek podczas wysyłki: {error}", flush=True)
                else:
                    # ustawienie statusu na ok w przypadku braku zagrozenia
                    self.status = STATUS.OK
                    self.warning_time = None

                # rest liczników
                self.total_pir26 = 0
                self.total_pir16 = 0
                self.total_cam_motion = False
            time.sleep(self._main_interval)

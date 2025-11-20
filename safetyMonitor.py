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

def sendAlertEmail(users_in: tuple[list], current_pir26, current_pir16, people_in_danger, frame):
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
        f"   • PIR26: {current_pir26} detekcji\n"
        f"   • PIR16: {current_pir16} detekcji\n"
        f"   • Kamera: Brak ruchu\n"
        f"   • Liczba osób w obręcbie kamery: {people_in_danger}\n\n"
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
        except Exception as e:
            print(f"[SafetyMonitor] Błąd dodawania obrazka: {e}", flush=True)
    else:
        print("[SafetyMonitor] Brak klatki z kamery", flush=True)

    try:
        with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
            server.starttls()
            server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            server.send_message(msg)
            print("[SafetyMonitor] Wysłano maila alarmowego!", flush=True)
            return True
    except Exception as e:
        print(f"[SafetyMonitor] Błąd wysyłania maila: {e}", flush=True)
        return False


class SafetyMonitor:
    def __init__(self, pir_monitor: PIRMonitor, cam_monitor: CAMMonitor, card_monitor: CardMonitor,
                alert_interval=(60*5)) -> None:
        """
        Args:
            pir_interval: Jak często sprawdzać PIR (sekundy) - dla UI
            cam_interval: Jak często sprawdzać kamerę (sekundy) - dla UI
            alert_interval: Jak często sprawdzać warunki alarmu (sekundy) - dla wysyłki maila
        """
        self.pir_monitor = pir_monitor
        self.cam_monitor = cam_monitor
        self.card_monitor = card_monitor
        self.alert_interval = alert_interval
        self.working = True
        
        # Dane z czujników (aktualizowane często)
        self.current_pir26 = 0
        self.current_pir16 = 0
        self.total_pir26 = 0
        self.total_pir16 = 0
        self.people_in_danger = 0
        
        # Czasy ostatnich sprawdzeń
        self.last_pir_check = time.time()
        self.last_cam_check = time.time()
        self.last_alert_check = time.time()
        
        # Stany alarmów (aktualizowane często - dla UI)
        self.pir_alarm = False
        self.current_cam_alarm = False
        self.general_cam_alarm = False
        
        # Stan głównego zagrożenia (aktualizowany rzadko - dla maili)
        self.danger = False
        self.main_alert_on = True
        self.email_sent = False
        
        self.thread = threading.Thread(target=self.startAlerts, daemon=True)
        print(f"[SafetyMonitor] Inicjalizacja:", flush=True)
        print(f" ALERT: co {alert_interval}s", flush=True)

    def startThread(self):
        self.thread.start()
        print("[SafetyMonitor] Wątek uruchomiony", flush=True)

    def getPirData(self):
        pir26 = self.pir_monitor.getPirCounter(26)
        pir16 = self.pir_monitor.getPirCounter(16)
        self.total_pir26 += pir26
        self.total_pir16 += pir16
        if pir26 is not None or pir16 is not None:
            if pir26 > 0 or pir16 > 0:
                self.pir_alarm = False
                print(f"[SafetyMonitor] PIR OK: Ruch wykryty (PIR26={pir26}, PIR16={pir16})", flush=True)
            else:
                self.pir_alarm = True
                print(f"[SafetyMonitor] PIR ALARM: Brak ruchu! (PIR26={pir26}, PIR16={pir16})", flush=True)
            
            self.pir_monitor.restCounters()
        else:
            self.pir_alarm = False
            print("[SafetyMonitor] Brak danych z PIR", flush=True)
        return pir26, pir16
    
    def getCamData(self):
        print(f"[SafetyMonitor] Sprawdzam kamerę...", flush=True)
        cam_motion = self.cam_monitor.motion_saftey
        self.people_in_danger = self.cam_monitor.people_count
        cam_alarm = False
        if cam_motion:
            cam_alarm = False
            print(f"[SafetyMonitor] CAM OK: Ruch wykryty, osób={self.people_in_danger}", flush=True)
        else:
            self.general_cam_alarm = True
            cam_alarm = True
            print(f"[SafetyMonitor] CAM ALARM: Brak ruchu! Osób={self.people_in_danger}", flush=True)
        self.cam_monitor.motion_saftey = False
        return cam_motion, self.people_in_danger, cam_alarm

    # def updatePirAlarm(self):
    #     # ===== SPRAWDZANIE PIR (częste - dla UI) =====
    #     print(f"\n[SafetyMonitor] Update PIR...", flush=True)
        
    #     self.current_pir26 = self.pir_monitor.getPirCounter(26)
    #     self.current_pir16 = self.pir_monitor.getPirCounter(16)
        
    #     self.total_pir26 += self.current_pir26
    #     self.total_pir16 += self.current_pir16
    #     if self.current_pir26 is not None or self.current_pir16 is not None:
    #         if self.current_pir26 > 0 or self.current_pir16 > 0:
    #             self.pir_alarm = False
    #             print(f"[SafetyMonitor] PIR OK: Ruch wykryty (PIR26={self.current_pir26}, PIR16={self.current_pir16})", flush=True)
    #         else:
    #             self.pir_alarm = True
    #             print(f"[SafetyMonitor] PIR ALARM: Brak ruchu! (PIR26={self.current_pir26}, PIR16={self.current_pir16})", flush=True)
            
    #         self.pir_monitor.restCounters()
    #     else:
    #         self.pir_alarm = False
    #         print("[SafetyMonitor] Brak danych z PIR", flush=True)

    # def updateCamAlarm(self):
    #     # ===== SPRAWDZANIE KAMERY (częste - dla UI) =====
    #     print(f"[SafetyMonitor] Sprawdzam kamerę...", flush=True)
    #     cam_motion = self.cam_monitor.motion_saftey
    #     self.people_in_danger = self.cam_monitor.people_count
        
    #     if cam_motion:
    #         self.cam_alarm = False
    #         print(f"[SafetyMonitor] CAM OK: Ruch wykryty, osób={self.people_in_danger}", flush=True)
    #     else:
    #         self.cam_alarm = True
    #         self.current_cam_alarm = True
    #         print(f"[SafetyMonitor] CAM ALARM: Brak ruchu! Osób={self.people_in_danger}", flush=True)
        
    #     self.cam_monitor.motion_saftey = False

    def startAlerts(self):
        print("[SafetyMonitor] Monitoring rozpoczęty", flush=True)
        
        while self.working:
            iteration_time = time.time()
            # SPRAWDZANIE GŁÓWNEGO ALERTU
            if iteration_time - self.last_alert_check >= self.alert_interval and self.main_alert_on:
                self.getPirData()
                self.getCamData()
                print(f"[SafetyMonitor] SPRAWDZANIE GŁÓWNEGO ALARMU", flush=True)
                print(f"  Człowiek w środku: {self.card_monitor.human_in}", flush=True)
                print(f"  Alarm kamery: {self.general_cam_alarm}", flush=True)
                print(f"  Alarm PIR: {self.pir_alarm}", flush=True)
                
                # DANGER = wszystkie warunki spełnione TERAZ
                if self.general_cam_alarm and self.total_pir26 == 0 and self.total_pir16 == 0 and self.card_monitor.human_in:
                    self.danger = True
                    print(f"{'='*60}", flush=True)
                    print(f"[SafetyMonitor] !!!! DANGER !!!!", flush=True)
                    print(f"  Brak ruchu przy obecności człowieka przez {self.alert_interval}s!", flush=True)
                    print(f"{'='*60}\n", flush=True)
                    
                    # WYSYŁKA MAILA (tylko raz)
                    if not self.email_sent:
                        print("[SafetyMonitor] Wysyłam mail alarmowy...", flush=True)
                        try:
                            if sendAlertEmail(
                                self.card_monitor.users_in,
                                self.current_pir26,
                                self.current_pir16,
                                self.people_in_danger,
                                self.cam_monitor.streamed_frame
                            ):
                                self.email_sent = True
                                print("[SafetyMonitor] Mail wysłany pomyślnie", flush=True)
                                self.main_alert_on = False
                            else:
                                print("[SafetyMonitor] Nie udało się wysłać maila", flush=True)
                        except Exception as e:
                            print(f"[SafetyMonitor] Wyjątek podczas wysyłki: {e}", flush=True)
                else:
                    print(f"[SafetyMonitor] Warunki alarmu NIE spełnione - OK", flush=True)
                    if self.danger:
                        print(f"[SafetyMonitor] Sytuacja bezpieczna", flush=True)
                    self.danger = False
                
                print(f"{'='*60}\n", flush=True)
                self.last_alert_check = iteration_time
                self.total_pir26 = 0
                self.total_pir16 = 0
                self.general_cam_alarm = False
            time.sleep(self.alert_interval)
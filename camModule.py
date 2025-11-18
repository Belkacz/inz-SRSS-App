from typing import List, Tuple
from dataclasses import dataclass
import threading
import time
import mediapipe
import numpy as np
import cv2
import websocket
from cardModule import CardMonitor

@dataclass
class Box:
    x1: int
    y1: int
    x2: int
    y2: int
    conf: float

PERSON_COLORS = [
        (0, 255, 0),   # zielony – osoba 1
        (0, 0, 255),   # czerwony – osoba 2
        (255, 0, 0)    # niebieski – osoba 3
    ]
class FrameAnalyser:
    def __init__(self) -> None:
        self.mp_pose = mediapipe.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=0,
            min_detection_confidence=0.5
        )
        self.max_people = 3  # Maksymalnie szukaj 3 osób

    def erase_person(self, img, pt1, pt2):
        x1, y1 = pt1
        x2, y2 = pt2
        
        h, w = img.shape[:2]
        width = x2 - x1
        height = y2 - y1
        
        # MARGINES - 20%
        margin_x = int(0.2 * width)
        margin_y = int(0.2 * height)
        
        x1_new = max(0, x1 - margin_x)
        x2_new = min(w, x2 + margin_x)
        y1_new = max(0, y1 - margin_y)
        y2_new = min(h, y2 + margin_y)
        
        # Czarny prostokąt
        cv2.rectangle(img, (x1_new, y1_new), (x2_new, y2_new), (0, 0, 0), -1)
        return img

    def FindPeople(self, frame) -> Tuple[int, List[Box]]:
        try:
            boxes_data = []
            working_frame = frame.copy()
            h, w = frame.shape[:2]
            
            min_box_area = 8000  # Minimalna powierzchnia (odrzuć małe fragmenty)
            min_visibility = 60  # Minimalna visibility w %
            
            for iteration in range(self.max_people):
                # Debug
                if iteration == 0:
                    cv2.imwrite("debug_working_frame_iter0.jpg", working_frame)
                
                # MediaPipe
                rgb_frame = cv2.cvtColor(working_frame, cv2.COLOR_BGR2RGB)
                results = self.pose.process(rgb_frame)

                if results.pose_landmarks:
                    landmarks = results.pose_landmarks.landmark

                    x_coords = []
                    y_coords = []
                    visibility_sum = 0
                    landmarks_counter = 0

                    # Zbierz współrzędne
                    for landmark in landmarks:
                        x = int(landmark.x * w)
                        y = int(landmark.y * h)
                        vis = landmark.visibility if landmark.visibility is not None else 0

                        x_coords.append(x)
                        y_coords.append(y)
                        visibility_sum += vis
                        landmarks_counter += 1

                    # Bounding box
                    x1 = int(max(0, min(x_coords)))
                    y1 = int(max(0, min(y_coords)))
                    x2 = int(min(w, max(x_coords)))
                    y2 = int(min(h, max(y_coords)))

                    # FILTR 1: Powierzchnia boxa
                    box_area = (x2 - x1) * (y2 - y1)
                    if box_area < min_box_area:
                        print(f"[FrameAnalyser] ✗ Odrzucono iter {iteration+1}: za mały box ({box_area} px < {min_box_area})", flush=True)
                        break

                    # FILTR 2: Visibility
                    visibility_percent = (visibility_sum / landmarks_counter * 100) if landmarks_counter > 0 else 0
                    # if visibility_percent < min_visibility:
                    #     print(f"[FrameAnalyser] ✗ Odrzucono iter {iteration+1}: niska visibility ({visibility_percent:.1f}% < {min_visibility}%)", flush=True)
                    #     break
                    
                    # Dodaj box
                    box = Box(x1, y1, x2, y2, visibility_percent)
                    boxes_data.append(box)

                    print(f"[FrameAnalyser] ✓ Osoba #{iteration+1}: area={box_area}px, vis={visibility_percent:.1f}%", flush=True)

                    # WYMAŻ z dużym marginesem
                    working_frame = self.erase_person(working_frame, (x1, y1), (x2, y2))
                    # working_frame = self.erase_person_ellipse(working_frame, (x1, y1), (x2, y2), (0, 0, 0), thickness=-1)
                    
                    # Debug
                    cv2.imwrite(f"debug_after_erase_person{iteration+1}.jpg", working_frame)
                    
                else:
                    print(f"[FrameAnalyser] ✗ Nie znaleziono więcej osób po {iteration} iteracjach", flush=True)
                    break
            
            print(f"[FrameAnalyser] Wykryto łącznie {len(boxes_data)} osób\n", flush=True)
            return len(boxes_data), boxes_data
            
        except Exception as e:
            print(f"[FrameAnalyser] BŁĄD: {e}", flush=True)
            import traceback
            traceback.print_exc()
            return 0, []


    def DrawBox(self, frame, boxes: List[Box], people_count):
        line_poeple_size = 2
        line_conf_size = 1
        drawed_frame = frame.copy()
        if(people_count > 0):
            for idx, box in enumerate(boxes):
                cv2.rectangle(drawed_frame, (box.x1, box.y1), (box.x2, box.y2), (0, 255, 0), 1)
                cv2.putText(drawed_frame, f"conf: {box.conf:.2f}", (box.x1-10, box.y1-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), line_conf_size)

        cv2.putText(drawed_frame, f"Ludzi: {people_count}",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), line_poeple_size)
        return drawed_frame


class MotionDetector:
    def __init__(self, threshold=25, min_area=5000):
        self.threshold = 15
        self.min_area = min_area
        self.dead_zone = 30
        self.gaus_blur = 15

    def detectMotion(self, frame, prev_frame) -> bool:
        if frame.shape != prev_frame.shape:
            prev_frame = cv2.resize(prev_frame, (frame.shape[1], frame.shape[0]))

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        cv2.imwrite("gray.jpg", gray)
        gray = cv2.GaussianBlur(gray, (self.gaus_blur, self.gaus_blur), 0)
        cv2.imwrite("GaussianBlur.jpg", gray)

        prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
        prev_gray = cv2.GaussianBlur(prev_gray, (self.gaus_blur, self.gaus_blur), 0)

        frame_delta = cv2.absdiff(prev_gray, gray)
        _, thresh = cv2.threshold(frame_delta, self.threshold, 255, cv2.THRESH_BINARY)
        thresh = cv2.dilate(thresh, None, iterations=2)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.imwrite("thresh.jpg", thresh)
        motion_detected = False
        for contour in contours:
            if cv2.contourArea(contour) > self.min_area:
                motion_detected = True
                self.dead_zone = 15
                break
        
        if not motion_detected and self.dead_zone > 0:
            motion_detected = True
            self.dead_zone -= 1
        
        return motion_detected


class CAMMonitor:
    def __init__(self, ws_url: str, card_monitor: CardMonitor, 
                 detect_motion=True, find_people=True) -> None:
        self.ws_url = ws_url
        self.card_monitor = card_monitor
        self.thread = threading.Thread(target=self._ws_listener, daemon=True)
        self.active = True
        self.prev_frame = None
        self.last_frame = None
        self.stremed_frame = None
        self.placeholder_frame = cv2.imread("stand_by.jpg")
        self.find_people = find_people
        self.detect_motion = detect_motion
        self.frame_analyser = FrameAnalyser()
        self.motion_detector = MotionDetector()
        
        self.motion_detected = False
        self.people_count = 0
        self.frame_counter = 0
        self.anylyze_interval = 10
        self.detection_boxes = []
        
        self.frame_counter = 0
        self.analyze_interval = 10  # Co ile klatek analizować
        
        print(f"[CAMMonitor] Inicjalizacja: analyze_interval={self.analyze_interval}", flush=True)

    def startThread(self):
        self.thread.start()

    def _ws_listener(self):
        print("[DEBUG] Wątek ws_listener wystartował!", flush=True)
        
        while self.active:
            try:
                ws = websocket.WebSocket()
                ws.connect(self.ws_url)
                print(f"[CAMMonitor] ✓ Połączono z {self.ws_url}", flush=True)
                
                while self.active:
                    msg = ws.recv()
                    if not msg:
                        continue

                    if isinstance(msg, bytes):
                        nparr = np.frombuffer(msg, np.uint8)
                        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                        
                        if frame is not None:
                            # Aktualizuj klatki
                            if self.last_frame is not None:
                                self.prev_frame = self.last_frame
                            self.last_frame = frame
                            
                            # Inkrementuj licznik
                            self.frame_counter += 1
                            if self.frame_counter >= 60:
                                self.frame_counter = 0
                            
                            # DEBUG co 30 klatek
                            if self.frame_counter % 30 == 0:
                                print(f"[CAMMonitor] human_in={self.card_monitor.human_in}, "
                                      f"frame={self.frame_counter}, people={self.people_count}", flush=True)
                            
                            # Sprawdź czy ktoś jest
                            if not self.card_monitor.human_in:
                                # NIKT - wyzeruj
                                self.people_count = 0
                                self.detection_boxes = []
                                self.stremed_frame = self.frame_analyser.DrawBox(frame, [], 0)
                                continue
                            if self.detect_motion and self.prev_frame is not None:
                                self.motion_detected = self.motion_detector.detectMotion(
                                    self.last_frame, self.prev_frame
                                )

                            if self.find_people and self.frame_counter % self.analyze_interval == 0:
                                print(f"\n=== ANALIZA KLATKI {self.frame_counter} ===", flush=True)
                                self.people_count, self.detection_boxes = \
                                    self.frame_analyser.FindPeople(frame)
                                print(f"=== WYKRYTO: {self.people_count} osób ===\n", flush=True)
                            
                            # Rysuj
                            self.stremed_frame = self.frame_analyser.DrawBox(
                                frame, self.detection_boxes, self.people_count
                            )
                            
                        else:
                            print("[CAMMonitor] Błąd dekodowania klatki", flush=True)
                            self.stremed_frame = self.placeholder_frame.copy()

            except Exception as e:
                print(f"[CAMMonitor] ✗ BŁĄD: {e}", flush=True)
                import traceback
                traceback.print_exc()
                self.stremed_frame = self.placeholder_frame.copy()
                time.sleep(5)

    def get_frame(self):
        return self.last_frame
    
    def generate_frames(self):
        """Generator dla Flask MJPEG stream"""
        while True:
            if self.stremed_frame is None:
                time.sleep(0.1)
                continue

            ret, buffer = cv2.imencode('.jpg', self.stremed_frame, 
                                     [cv2.IMWRITE_JPEG_QUALITY, 80])
            if not ret:
                time.sleep(0.1)
                continue

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            
            time.sleep(0.033)
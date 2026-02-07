from flask import Flask
from routes import register_routes
from pirModule import PIRMonitor
from camModule import CAMMonitor
from cardModule import CardMonitor, UserHandler
from safetyMonitor import SafetyMonitor
from settings import settings

# interwały do wszczęcia działania
WARNING_INTERVAL = 60
ALARM_REFRESH = 5 * 60

# timeouty WebSocket
RECONNECT_DELAY = 5.0      # czas ponownego łączenia
EMPTY_MSG_DELAY = 0.1      # opóźnienie przy pustej wiadomości
ERROR_DELAY = 0.5          # opóźnienie po błędzie przetwarzania
WS_TIMEOUT_DELAY = 0.1     # timeout WebSocket (tylko CAMMonitor)

def main():
    app = Flask(__name__)
    
    # stworzenie instancji klas
    pir_monitor = PIRMonitor(settings.WS_SERVER_URL,
        reconnect_delay=RECONNECT_DELAY, empty_msg_delay=EMPTY_MSG_DELAY, error_delay=ERROR_DELAY)
    user_handler = UserHandler(settings.DB_URL)
    card_monitor = CardMonitor(settings.WS_CARD_URL,
        user_handler,reconnect_delay=RECONNECT_DELAY,empty_msg_delay=EMPTY_MSG_DELAY,error_delay=ERROR_DELAY)
    cam_monitor = CAMMonitor(settings.WS_CAMERA_URL,
        reconnect_delay=RECONNECT_DELAY, empty_msg_delay=EMPTY_MSG_DELAY, ws_timeout_delay=WS_TIMEOUT_DELAY)
    
    safety_monitor = SafetyMonitor(pir_monitor, cam_monitor, card_monitor, WARNING_INTERVAL, ALARM_REFRESH)
    register_routes(app, pir_monitor, safety_monitor, cam_monitor, card_monitor)
    
    # start wątków klas
    pir_monitor.startThread()
    card_monitor.startThread()
    cam_monitor.startThread()
    safety_monitor.startThread()
    
    # start Flask
    app.run(host='0.0.0.0', port=5000, use_reloader=False)
if __name__ == "__main__":
    main()
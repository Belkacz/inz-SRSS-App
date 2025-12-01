from flask import Flask
from routes import register_routes
from pirModule import PIRMonitor
from camModule import CAMMonitor
from cardModule import CardMonitor, UserHandler
from safetyMonitor import SafetyMonitor
from settings import settings
# from dotenv import load_dotenv
import os

WARNING_INTERVAL = 60
ALARM_REFRESH = 5 * 60

def main():
    app = Flask(__name__)

    pir_monitor = PIRMonitor(settings.WS_SERVER_URL)
    user_handler = UserHandler(settings.DB_URL)
    card_monitor = CardMonitor(settings.WS_CARD_URL, user_handler)
    cam_monitor = CAMMonitor(settings.WS_CAMERA_URL, card_monitor)
    
    safety_monitor = SafetyMonitor(pir_monitor, cam_monitor, card_monitor, WARNING_INTERVAL, ALARM_REFRESH)
    register_routes(app, pir_monitor, safety_monitor, cam_monitor, card_monitor)

    pir_monitor.startThread()

    card_monitor.startThread()

    cam_monitor.startThread()

    safety_monitor.startThread()

    # --- Start Flask
    app.run(host='0.0.0.0', port=5000, use_reloader=False)
if __name__ == "__main__":
    main()


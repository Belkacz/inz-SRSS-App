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

GENERAL_REFRESH = 30


def main():
    app = Flask(__name__)

    pir_monitor = PIRMonitor(settings.WS_SERVER_URL)
    # alarm_pir = AlertPir(settings.WS_SERVER_URL, pir_monitor, alarm_manager, 30)
    user_handler = UserHandler(settings.DB_URL)
    card_monitor = CardMonitor(settings.WS_CARD_URL, user_handler)
    cam_monitor = CAMMonitor(settings.WS_CAMERA_URL, card_monitor)
    
    safety_monitor = SafetyMonitor(pir_monitor, cam_monitor, card_monitor, GENERAL_REFRESH)
    register_routes(app, pir_monitor, safety_monitor, cam_monitor, card_monitor)

    pir_monitor.startThread()

    card_monitor.startThread()

    cam_monitor.startThread()

    safety_monitor.startThread()

    # --- Start Flask
    app.run(host='0.0.0.0', port=5000, use_reloader=False)
if __name__ == "__main__":
    main()


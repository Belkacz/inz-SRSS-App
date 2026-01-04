import time
from flask import Response, jsonify, render_template, request
import camModule
from safetyMonitor import STATUS

def register_routes(app, pir_monitor, safety_monitor, cam_monitor, card_monitor):
    # enpoint zwcający dane z głównego systemu alertowego
    @app.route("/api/general_status", methods=["GET", "PATCH"])
    def get_general_alert():
        # patch dla resetu systemu
        if request.method == "PATCH":
            data = request.get_json(force=True)

            if data.get("generalReset"):

                safety_monitor.resetData()
                return jsonify(
                    {
                    "status": "reset_ok",
                    "nextRefreshIn": safety_monitor._main_interval
                    }
                )

            return jsonify({"status": "no_action"}), 400

        # GET – zwracanie statusu
        warning_passed_time = 0
        if(safety_monitor.warning_time != None and safety_monitor.status == STATUS.WARNING):
            warning_passed_time = int(time.time() - safety_monitor.warning_time)
        status = {
            "monitorStatus" : safety_monitor.status.value,
            "alertCountdown":  safety_monitor.alert_interval - warning_passed_time,
            "nextRefreshIn": safety_monitor._main_interval
        }
        return jsonify(status)
    
    # enpoint zwracjący dane z czujników i kamer
    @app.route("/api/sensors_status")
    def get_sensor_status():
        sensors_data = safety_monitor.getSensorData()
        status = {
            "pirData": {
                "pir26": sensors_data["pir26"],
                "pir16": sensors_data["pir16"],
                "alarmStatus": sensors_data["pir_alarm"],
                "pirConnected": pir_monitor.pir_connected
            },
            "camData": {
                "motionDetected": sensors_data['cam_motion'],
                "peopleCount": sensors_data['people_count'],
                "camConnected": cam_monitor.cam_connected
            },
            "timestamp": sensors_data["timestamp"]
        }
        return jsonify(status)
    
    # zwrot html z klatkami
    @app.route('/video_feed')
    def video_feed():
        return Response(cam_monitor.generateFrames(),
                        mimetype='multipart/x-mixed-replace; boundary=frame')
    
    # dane z systemu card i zalogowanych użytkowników
    @app.route('/users')
    def get_users():
        users_in_json = []
        for user_in in card_monitor.users_in:
            users_in_json.append(
                {
                    "card_number": user_in.card_number,
                    "first_name": user_in.first_name,
                    "second_name": user_in.second_name,
                    "email": user_in.email,
                    "supervisor": user_in.supervisor,
                }
            )
        users_out_json = []
        for user_out in card_monitor.users_out:
            users_out_json.append(
                {
                    "card_number": user_out.card_number,
                    "first_name": user_out.first_name,
                    "second_name": user_out.second_name,
                    "email": user_out.email,
                    "supervisor": user_out.supervisor,
                }
            )
            
        return jsonify({
        "usersIn": users_in_json,
        "usersOut": users_out_json,
        "cardConnected": card_monitor.connected 
    })

    # wystawienie template
    @app.route('/')
    def home():
        return render_template("index.html")

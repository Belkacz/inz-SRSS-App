import time
from flask import Response, jsonify, render_template, request
import camModule
from safetyMonitor import STATUS

def register_routes(app, pir_monitor, safety_monitor, cam_monitor, card_monitor):
    @app.route('/pir', methods=['GET'])
    def get_pir_data():
        data_copy = pir_monitor.get_data()
        print(f"[DEBUG routes.py] last_pir_data = {data_copy}")
        return jsonify(data_copy)

    # @app.route('/alarm', methods=['GET'])
    # def get_alarm_status():
    #     alarm_status = alarm_manager.PirAlarm
    #     return jsonify({
    #         'alarm': alarm_status,
    #         'message': 'Brak aktywności!' if alarm_status else 'System aktywny'
    #     })
    # @app.route("/api/set_fps", methods=["GET", "PATCH"])
    # def setFPS():
    #     if request.method == "PATCH":
    #         data = request.get_json(force=True)
    #         if data.get("FPS"):
    #             cam_monitor.setSteamFPS(data.FPS)
    @app.route("/api/general_status", methods=["GET", "PATCH"])
    def get_general_alert():
        if request.method == "PATCH":
            data = request.get_json(force=True)

            if data.get("generalReset"):

                safety_monitor.resetData()
                # safety_monitor.reset_alert_timer() 
                print("[API] Reset alarmu — ustawiono danger = False")

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
    
    @app.route('/video_feed')
    def video_feed():
        return Response(cam_monitor.generateFrames(),
                        mimetype='multipart/x-mixed-replace; boundary=frame')
    
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
        "users_in": users_in_json,
        "users_out": users_out_json
    })

    @app.route('/')
    def home():
        return render_template("index.html")

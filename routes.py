import time
from flask import Response, jsonify, render_template

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

    @app.route("/api/status_pir")
    def get_status():
        status = {
            "pir26Counter": safety_monitor.current_pir26,
            "pir16Counter": safety_monitor.current_pir16,
            "alarmStatus": safety_monitor.pir_alarm,
            "currentInterval": safety_monitor.pir_interval,
            "nextRefreshIn": int(safety_monitor.pir_interval- ((time.time() - int(safety_monitor.last_pir_check)) % safety_monitor.pir_interval))
        }
        return jsonify(status)
    
    @app.route("/api/cam_status")
    def get_cam_status():
        status = {
            "motionDetected": getattr(safety_monitor.cam_monitor, "motion_detected", False),
            "peopleCount": getattr(safety_monitor.cam_monitor, "people_count", 0),
            "currentInterval": safety_monitor.cam_interval,
            "nextRefreshIn":  int(safety_monitor.cam_interval - ((time.time() - safety_monitor.last_cam_check) % safety_monitor.cam_interval))
        }
        return jsonify(status)

    @app.route('/video_feed')
    def video_feed():
        return Response(cam_monitor.generate_frames(),
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

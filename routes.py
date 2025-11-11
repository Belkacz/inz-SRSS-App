import time
from flask import Response, jsonify, render_template

def register_routes(app, pir_monitor, alarm_manager, alarm_pir, cam_monitor, card_monitor):
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

    @app.route("/api/status")
    def get_status():
        status = {
            "pir26Counter": alarm_pir.getPirCounter(26),
            "pir16Counter": alarm_pir.getPirCounter(16),
            "alarmStatus": alarm_manager.getPirAlarm(),
            "currentInterval" : int(alarm_pir.checkInterval),
            "nextRefreshIn": int(alarm_pir.checkInterval - ((time.time() - alarm_pir.lastCounterRestTime) % alarm_pir.checkInterval))
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

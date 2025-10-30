import time, json, random
from datetime import datetime
from threading import Thread
import paho.mqtt.client as mqtt
from dotenv import load_dotenv
from devices.Ultrasonic import UltrasonicSensor
from devices.servo import ServoGate
from database.db_connect import DBManager
import os

# ==============================
# 환경 변수 로드
# ==============================
load_dotenv()
BROKER = os.getenv("BROKER_HOST")
PORT = int(os.getenv("BROKER_PORT"))
TOPIC_CMD = os.getenv("TOPIC_CMD")
TOPIC_CAR = os.getenv("TOPIC_CAR")

# ==============================
# 디바이스 초기화
# ==============================
sensor = UltrasonicSensor()
servo = ServoGate()
db = DBManager()  # ✅ DB 연결
sensor_active = False

# ==============================
# DB 차량 목록 가져오기
# ==============================
def get_registered_vehicles():
    try:
        vehicles = db.select_data("users", columns="user_id, vehicle_no")
        car_dict = {row["vehicle_no"]: row["user_id"] for row in vehicles if row["vehicle_no"]}
        print(f"🚘 DB 등록 차량 목록: {list(car_dict.keys())}")
        return car_dict
    except Exception as e:
        print(f"⚠️ 차량목록 불러오기 오류: {e}")
        return {}

# ==============================
# parking_log 테이블에 기록
# ==============================
def log_parking_event(user_id, car_no):
    try:
        # 1️⃣ 현재 차량이 아직 출차되지 않은 상태인지 확인
        query = f"SELECT parking_id, action FROM parking_log WHERE user_id = %s AND action = 'IN' ORDER BY in_time DESC LIMIT 1"
        cur = db.conn.cursor(dictionary=True)
        cur.execute(query, (user_id,))
        record = cur.fetchone()
        cur.close()

        # 2️⃣ 현재 주차 중이면 (IN 상태) → OUT으로 업데이트
        if record:
            sql = """
                UPDATE parking_log
                SET out_time = %s, action = 'OUT', note = %s
                WHERE parking_id = %s
            """
            note = f"등록 차량 출차 ({car_no})"
            cur = db.conn.cursor()
            cur.execute(sql, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), note, record["parking_id"]))
            db.conn.commit()
            cur.close()
            print(f"🚗 차량 출차 기록 업데이트 완료 → {car_no}")

       
            
    except Exception as e:
        print(f"⚠️ 주차 로그 처리 오류: {e}")

# ==============================
# 초음파 센서 루프
# ==============================
def sensor_loop():
    global sensor_active
    print("📡 초음파 센서 루프 시작")

    registered_cars = get_registered_vehicles()

    while sensor_active:
        try:
            distance = sensor.measure_distance()
            print(f"📏 거리: {distance:.2f} cm")

            if 0 < distance < 10:
                # 70% 등록 차량 / 30% 미등록 차량
                if random.random() < 0.7 and registered_cars:
                    car_no = random.choice(list(registered_cars.keys()))
                    user_id = registered_cars[car_no]
                else:
                    car_no = f"{random.randint(100,999)}가{random.randint(1000,9999)}"
                    user_id = None

                print(f"🚗 차량 감지 → {car_no}")

                # ✅ 등록 차량
                if user_id:
                    print(f"✅ 등록 차량 확인: {car_no}")
                    servo.open_async()
                    client.publish(TOPIC_CAR, json.dumps({
                    "carNo": car_no, 
                    "action": "authorized"
                    }, ensure_ascii=False))
                    log_parking_event(user_id, car_no)  # ✅ 이 한 줄로 변경
                    print("🔓 차단기 열림")


            # ❌ 미등록 차량
            else:
                print(f"🚫 미등록 차량: {car_no}")
                servo.close_async()
                message = {
                    "carNo": car_no, 
                    "action": "unauthorized",
                    "note": f"미등록 차량 접근 ({car_no})"
                }
                client.publish(TOPIC_CAR, json.dumps(message, ensure_ascii=False))
                log_parking_event(0, "DENY", message["note"])
                print("🔒 차단기 닫힘 유지")

                time.sleep(5)
            time.sleep(1.5)

        except Exception as e:
            print(f"⚠️ 센서 루프 오류: {e}")
            time.sleep(1)

# ==============================
# MQTT 콜백
# ==============================
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ MQTT 브로커 연결 성공")
        client.subscribe(TOPIC_CMD)
        print(f"📡 구독 완료 → {TOPIC_CMD}")
    else:
        print(f"❌ 연결 실패 (코드: {rc})")

def on_message(client, userdata, msg):
    global sensor_active
    payload = msg.payload.decode("utf-8")
    print(f"📩 수신 → {msg.topic}: {payload}")

    try:
        data = json.loads(payload)
        if data.get("action") == "activate":
            if not sensor_active:
                sensor_active = True
                print("🚗 센서 활성화 명령 수신")
                Thread(target=sensor_loop, daemon=True).start()
    except Exception as e:
        print(f"⚠️ 메시지 처리 오류: {e}")

# ==============================
# 메인 실행
# ==============================
client = mqtt.Client("pi_parking_client")
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT, 60)

try:
    print("🚀 스마트 주차 시스템 실행 중...")
    client.loop_forever()
except KeyboardInterrupt:
    print("🛑 프로그램 종료")
    sensor.cleanup()
    servo.cleanup()

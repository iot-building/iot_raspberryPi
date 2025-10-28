import os
import json
import random
import time
import paho.mqtt.client as mqtt
from dotenv import load_dotenv
from devices.Ultrasonic import UltrasonicSensor
from devices.servo import ServoGate

# ✅ .env 파일 불러오기
load_dotenv()

# ==============================
# 환경변수에서 MQTT 설정 불러오기
# ==============================
BROKER = os.getenv("BROKER_HOST")
PORT = int(os.getenv("BROKER_PORT"))
TOPIC_CMD = os.getenv("TOPIC_CMD")
TOPIC_CAR = os.getenv("TOPIC_CAR")

# ==============================
# 장치 초기화
# ==============================
sensor = UltrasonicSensor()
servo = ServoGate()

client = mqtt.Client("pi_parking_client")

# ==============================
# 차량번호 생성 함수
# ==============================
def random_car():
    prefix = random.choice(["111가", "222나", "333다", "397로", "123가"])
    suffix = str(random.randint(1000, 9999))
    return prefix + suffix

# ==============================
# 센서 루프
# ==============================
def run_sensor_loop():
    print("🚗 주차장 센서 활성화됨! 차량 감지 시작...")
    try:
        while True:
            dist = sensor.measure_distance()
            print(f"📏 거리: {dist} cm")

            if 0 < dist < 10:
                car_no = random_car()
                payload = json.dumps({"carNo": car_no})
                client.publish(TOPIC_CAR, payload)
                print(f"📤 차량 감지 → 전송: {payload}")

                # 🚗 문 열기 → 대기 → 닫기
                servo.open_async()
                time.sleep(4)
                servo.close_async()

                time.sleep(5)
            time.sleep(1)
    except KeyboardInterrupt:
        servo.cleanup()
        print("🛑 센서 루프 종료")

# ==============================
# MQTT 콜백 함수
# ==============================
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"✅ MQTT 브로커 연결 성공 → {BROKER}:{PORT}")
        client.subscribe(TOPIC_CMD)
        print(f"📡 명령 대기중 ({TOPIC_CMD})...")
    else:
        print("❌ 연결 실패. 코드:", rc)

def on_message(client, userdata, msg):
    payload = msg.payload.decode('utf-8').strip()
    print(f"📩 명령 수신 → {payload}")

    try:
        data = json.loads(payload)
        action = data.get("action", "")
        if action == "activate":
            run_sensor_loop()
        else:
            print("⚠️ 알 수 없는 명령:", action)
    except Exception as e:
        print("⚠️ 명령 처리 오류:", e)

# ==============================
# MQTT 설정
# ==============================
client.on_connect = on_connect
client.on_message = on_message

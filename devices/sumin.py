import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
import pymysql 
import time

# ===============================
# 🔧 환경 설정
# ===============================
SERVO_PIN = 11  
OPEN_DC = 7.5
CLOSE_DC = 2.5
OPEN_DURATION = 3  # 문 열려있는 시간

# mode = GPIO.getmode()
# if mode == GPIO.BOARD:
#     SERVO_PIN = 17      # 주황색 선이 물리 핀 17에 꽂혀 있음
# elif mode == GPIO.BCM:
#     SERVO_PIN = 0       # BCM에서 핀17은 존재하지 않음 (사용 불가)
# else:
#     raise RuntimeError("GPIO mode not set properly.")
# GPIO.setup(SERVO_PIN, GPIO.OUT)
# servo = GPIO.PWM(SERVO_PIN, 50)
# servo.start(CLOSE_DC)


DB_CONFIG = {
    "host": "192.168.14.74",
    "user": "sample",
    "password": "tnalsdlchlrhdi!",
    "db": "smartbuilding4",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor
}

# ===============================
# 🧠 함수 정의
# ===============================
reader = SimpleMFRC522()
GPIO.setup(SERVO_PIN, GPIO.OUT)
servo = GPIO.PWM(SERVO_PIN, 50)
servo.start(CLOSE_DC)

def db_connect():
    return pymysql.connect(**DB_CONFIG)

def is_member_card(card_id):
    """member 계정의 card_id가 맞는지 DB에서 확인"""
    try:
        conn = db_connect()
        with conn.cursor() as cur:
            sql = """
                SELECT name, id, is_active
                FROM users
                WHERE card_id = 'memberCard'
                LIMIT 1
            """ 
            cur.execute(sql)
            row = cur.fetchone()
            conn.close()
            if row and int(row["is_active"]) == 1:
                return True, row["name"]
            else:
                return False, None
    except Exception as e:
        print("❌ DB 오류:", e)
        return False, None

def open_door():
    print("🔓 문이 열립니다.")
    servo.ChangeDutyCycle(OPEN_DC)
    time.sleep(0.5)
    servo.ChangeDutyCycle(0)
    time.sleep(OPEN_DURATION)
    close_door()

def close_door():
    print("🔒 문이 닫힙니다.")
    servo.ChangeDutyCycle(CLOSE_DC)
    time.sleep(0.5)
    servo.ChangeDutyCycle(0)
def log_event(card_id, user_name, success):
    """출입 시도 이벤트 로그 기록"""
    try:
        conn = db_connect()
        with conn.cursor() as cur:
            sql = """
                INSERT INTO event_log (card_id, user_name, event_time, success)
                VALUES (%s, %s, NOW(), %s)
            """
            cur.execute(sql, (card_id, user_name, int(success)))
            conn.commit()
    except Exception as e:
        print("⚠️ 로그 기록 중 오류:", e)
    finally:
        conn.close()
# ===============================
# 🚪 메인 루프
# ===============================
try:
    print("===================================")
    print(" RFID 카드를 리더기에 대주세요...")
    print("===================================")

    while True:
        card_id, text = reader.read()
        print(f"\n[RFID 감지됨] ID={card_id}")

        authorized, user_name = is_member_card(card_id)
        if authorized:
            print(f"✅ {user_name} 님 (member 계정) → 출입 허가됨")
            open_door()
        else:
            print("🚫 시연용 memberCard가 아닙니다. 문을 열지 않습니다.")
        time.sleep(1)

except KeyboardInterrupt:
    print("\n🛑 종료합니다.")
finally:
    servo.stop()
    GPIO.cleanup()
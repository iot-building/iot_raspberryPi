import time
import board
import adafruit_dht
import mysql.connector
from mysql.connector import Error

# ===============================
# DB 설정 (MacBook의 MySQL 서버)
# ===============================
DB_CONFIG = {
    "host": "192.168.14.74",           # ✅ MacBook IP
    "user": "sample",                  # ✅ DB 사용자명
    "password": "tnalsdlchlrhdi!",     # ✅ 비밀번호
    "database": "smartbuilding4"       # ✅ DB 이름
}

# ===============================
# 센서 설정 (DHT11 or DHT22)
# ===============================
DHT_PIN = board.D25       # 실제 핀 번호
sensor = adafruit_dht.DHT11(DHT_PIN)  # DHT11 센서 사용 시
# sensor = adafruit_dht.DHT22(DHT_PIN)  # DHT22를 쓰는 경우 이 줄로 변경

DEVICE_ID = 1  # environment_data에 기록할 장치 ID (devices 테이블의 DHT 장치 번호)

# ===============================
# DB 연결 함수
# ===============================
def connect_db():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        if conn.is_connected():
            print("✅ MySQL 연결 성공")
            return conn
    except Error as e:
        print(f"❌ DB 연결 실패: {e}")
        return None

# ===============================
# 데이터 저장 함수
# ===============================
def insert_environment_data(conn, temperature, humidity):
    try:
        cursor = conn.cursor()
        sql = """
            INSERT INTO environment_data (device_id, temperature, humidity)
            VALUES (%s, %s, %s)
        """
        cursor.execute(sql, (DEVICE_ID, temperature, humidity))
        conn.commit()
        print(f"💾 저장 완료 → T={temperature:.1f}°C, H={humidity:.1f}%")
    except Error as e:
        print(f"DB 저장 실패: {e}")

# ===============================
# 메인 루프
# ===============================
def main():
    conn = connect_db()
    if not conn:
        print("DB 연결 불가. 종료합니다.")
        return

    print("🌡️ DHT 센서 데이터 수집 시작 (5초마다 업데이트)")
    try:
        while True:
            try:
                temperature = sensor.temperature
                humidity = sensor.humidity
                if temperature is not None and humidity is not None:
                    insert_environment_data(conn, temperature, humidity)
                else:
                    print("⚠️ 센서 데이터 읽기 실패, 다시 시도 중...")
            except RuntimeError as e:
                print(f"센서 오류: {e}")
            time.sleep(5)
    except KeyboardInterrupt:
        print("\n🛑 사용자 중단. 프로그램 종료.")
    finally:
        sensor.exit()
        conn.close()
        print("🔒 DB 연결 종료")

# ===============================
if __name__ == "__main__":
    main()
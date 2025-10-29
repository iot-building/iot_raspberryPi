import time, json, math, os
import board, busio, digitalio
from adafruit_mcp3xxx.mcp3008 import MCP3008, P0
from adafruit_mcp3xxx.analog_in import AnalogIn
import adafruit_dht
import mysql.connector
from mysql.connector import Error
import paho.mqtt.publish as publish

# ===============================
# DB 설정
# ===============================
DB = {
    "host": "192.168.14.74",
    "user": "sample",
    "password": "tnalsdlchlrhdi!",
    "database": "smartbuilding4"
}

# ===============================
# 장치 매핑
# ===============================
DEVICE_DHT = 7    # DHT-202B
DEVICE_MQ2 = 10    # MQ2-202B
DEVICE_HVAC = 9   # HVAC-202B
OFFICE_ID = 1      # 202B 오피스
USER_ID = None     # 자동 발생 이벤트

# ===============================
# 센서 및 임계값 설정
# ===============================
VCC = 5.0
RL_KOHM = 5.0
R0_PATH = "/home/pi/iot_raspberryPi/test/mq2_r0.json"
GAS_THRESHOLD = 500.0
TEMP_THRESHOLD = 30.0
HUMIDITY_LOW = 25.0
DHT_PIN = board.D25
dht = adafruit_dht.DHT11(DHT_PIN)

# ===============================
# 공통 함수
# ===============================
def connect_db():
    try:
        conn = mysql.connector.connect(**DB)
        if conn.is_connected():
            return conn
    except Error as e:
        print(f"❌ DB 연결 실패: {e}")
    return None

def load_r0(path):
    with open(path) as f:
        return json.load(f)["R0_ohm"]

def rs_from_voltage(vout):
    rl = RL_KOHM * 1000.0
    return rl * (VCC - vout) / vout if vout > 0 else math.inf

def ppm_from_ratio(ratio):
    p = {"x1": 200, "y1": 1.7, "x2": 10000, "y2": -0.38}
    X1, Y1 = math.log10(p["x1"]), p["y1"]
    X2, Y2 = math.log10(p["x2"]), p["y2"]
    m = (Y2 - Y1) / (X2 - X1)
    X = (math.log10(ratio) - Y1) / m + X1
    return 10 ** X

# ===============================
# DB 조작 함수
# ===============================
def insert_environment(conn, device_id, temp=None, hum=None, gas=None):
    sql = """
        INSERT INTO environment_data (device_id, temperature, humidity, gas_level)
        VALUES (%s, %s, %s, %s)
    """
    cur = conn.cursor()
    cur.execute(sql, (device_id, temp, hum, gas))
    conn.commit()
    cur.close()

def insert_event(conn, device_id, office_id, etype, action, value, note):
    sql = """
        INSERT INTO event_log (device_id, user_id, office_id, event_type, event_action, value, note)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    cur = conn.cursor()
    cur.execute(sql, (device_id, USER_ID, office_id, etype, action, value, note))
    conn.commit()
    cur.close()
    print(f"🚨 EVENT_LOG → [{etype}] {action} ({note})")

def update_device_status(conn, device_id, new_status):
    sql = "UPDATE devices SET status=%s, last_updated=NOW() WHERE device_id=%s"
    cur = conn.cursor()
    cur.execute(sql, (new_status, device_id))
    conn.commit()
    cur.close()
    print(f"🔄 DEVICE 상태 변경 → id={device_id}, status={new_status}")

# ===============================
# 메인 루프
# ===============================
def main():
    spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)
    cs = digitalio.DigitalInOut(board.D8)
    mcp = MCP3008(spi, cs)
    ain = AnalogIn(mcp, P0)
    R0 = load_r0(R0_PATH)

    conn = connect_db()
    if not conn:
        print("DB 연결 실패, 종료.")
        return

    print("🌡️ 환경 모니터링 시작 (5초 간격)")
    try:
        while True:
            try:
                temp = dht.temperature
                hum = dht.humidity
                vout = ain.voltage
                rs = rs_from_voltage(vout)
                ratio = rs / R0
                gas_ppm = ppm_from_ratio(ratio)

                print(f"T={temp:.1f}°C | H={hum:.1f}% | GAS={gas_ppm:.1f}ppm")

                insert_environment(conn, DEVICE_DHT, temp, hum, None)
                insert_environment(conn, DEVICE_MQ2, None, None, gas_ppm)

                # 이벤트 감지
                if gas_ppm > GAS_THRESHOLD:
                    insert_event(conn, DEVICE_MQ2, OFFICE_ID, "FIRE", "ALERT", f"{gas_ppm:.1f}", "가스농도 초과")
                    BROKER_IP = "192.168.14.74"
                    TOPIC_GAS = "building/gas"
                    update_device_status(conn, DEVICE_MQ2, "ALERT")
                    try:
                        publish.single(TOPIC_GAS, payload="ALERT", hostname=BROKER_IP)
                        print("📡 MQTT 발행 완료 → building/gas : ALERT")
                    except Exception as e:
                        print(f"⚠️ MQTT 발행 실패: {e}")
                else:
                    update_device_status(conn, DEVICE_MQ2, "IDLE")

                if temp > TEMP_THRESHOLD:
                    insert_event(conn, DEVICE_DHT, OFFICE_ID, "HVAC", "ON", f"{temp:.1f}", "냉방 작동")
                    update_device_status(conn, DEVICE_HVAC, "ON")
                elif hum < HUMIDITY_LOW:
                    insert_event(conn, DEVICE_DHT, OFFICE_ID, "HVAC", "ON", f"{hum:.1f}", "가습 작동")
                    update_device_status(conn, DEVICE_HVAC, "ON")
                else:
                    update_device_status(conn, DEVICE_HVAC, "IDLE")

            except RuntimeError as e:
                print(f"⚠️ 센서 읽기 오류: {e}")

            time.sleep(5)

    except KeyboardInterrupt:
        print("\n🛑 사용자 중단")
    finally:
        dht.exit()
        conn.close()
        print("🔒 DB 연결 종료")

if __name__ == "__main__":
    main()
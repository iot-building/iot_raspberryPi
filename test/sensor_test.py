import time, json, math, os
import board, busio, digitalio
from adafruit_mcp3xxx.mcp3008 import MCP3008, P0
from adafruit_mcp3xxx.analog_in import AnalogIn
import adafruit_dht
import mysql.connector
from mysql.connector import Error

# ===============================
# DB 설정 (MacBook의 MySQL 서버)
# ===============================
DB = {
    "host": "192.168.14.74",      # ✅ MacBook IP
    "user": "sample",
    "password": "tnalsdlchlrhdi!",
    "database": "smartbuilding4"
}

DEVICE_ID = 1   # devices 테이블 내 해당 장치 ID

# ===============================
# MQ-2 센서 설정
# ===============================
VCC = 5.0
RL_KOHM = 5.0
R0_PATH = "/home/pi/iot_raspberryPi/test/mq2_r0.json"
GAS_TYPE = "LPG"  # "LPG", "CO", "CH4" 등

def load_r0(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"⚠️ R0 파일 없음: {path}\n먼저 mq2_calibrate.py 실행 필요.")
    with open(path) as f:
        return json.load(f)["R0_ohm"]

def rs_from_voltage(vout, vcc=VCC, rl_kohm=RL_KOHM):
    rl = rl_kohm * 1000.0
    return rl * (vcc - vout) / vout if vout > 0 else math.inf

def ppm_from_ratio(ratio, gas="LPG"):
    params = {
        "LPG":  {"x1": 200, "y1": 1.7, "x2": 10000, "y2": -0.38},
        "CH4":  {"x1": 200, "y1": 2.3, "x2": 10000, "y2": -0.45},
        "CO":   {"x1": 200, "y1": 2.3, "x2": 10000, "y2": -0.48},
    }
    p = params[gas]
    X1, Y1 = math.log10(p["x1"]), p["y1"]
    X2, Y2 = math.log10(p["x2"]), p["y2"]
    m = (Y2 - Y1) / (X2 - X1)
    X = (math.log10(ratio) - Y1) / m + X1
    return 10 ** X

# ===============================
# DHT11 설정
# ===============================
DHT_PIN = board.D25
sensor_dht = adafruit_dht.DHT11(DHT_PIN)

# ===============================
# DB 연결 함수
# ===============================
def connect_db():
    try:
        conn = mysql.connector.connect(**DB)
        if conn.is_connected():
            print("✅ MySQL 연결 성공")
            return conn
    except Error as e:
        print(f"❌ DB 연결 실패: {e}")
    return None

# ===============================
# 데이터 저장 함수
# ===============================
def insert_data(conn, temp, hum, gas):
    try:
        cursor = conn.cursor()
        sql = """
            INSERT INTO environment_data (device_id, temperature, humidity, gas_level)
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(sql, (DEVICE_ID, temp, hum, gas))
        conn.commit()
        print(f"💾 저장 완료 → T={temp:.1f}°C, H={hum:.1f}%, GAS={gas:.1f}ppm\n")
    except Error as e:
        print(f"DB 저장 실패: {e}")

# ===============================
# 메인 루프
# ===============================
def main():
    # SPI/MQ-2 초기화
    spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)
    cs  = digitalio.DigitalInOut(board.D8)
    mcp = MCP3008(spi, cs)
    ain = AnalogIn(mcp, P0)
    R0 = load_r0(R0_PATH)
    print(f"🔧 MQ-2 R0={R0:,.0f}Ω, RL={RL_KOHM}kΩ, Gas={GAS_TYPE}")

    conn = connect_db()
    if not conn:
        print("DB 연결 실패. 종료합니다.")
        return

    print("🌡️ 온도·습도·가스 통합 측정 시작 (5초마다)")
    try:
        while True:
            try:
                # DHT11
                temp = sensor_dht.temperature
                hum = sensor_dht.humidity

                # MQ-2
                vout = ain.voltage
                rs = rs_from_voltage(vout)
                ratio = rs / R0
                gas_ppm = ppm_from_ratio(ratio, gas=GAS_TYPE)

                if temp is not None and hum is not None and gas_ppm is not None:
                    insert_data(conn, temp, hum, gas_ppm)
                else:
                    print("⚠️ 센서 데이터 읽기 실패, 다시 시도 중...")

            except RuntimeError as e:
                print(f"센서 오류: {e}")

            time.sleep(5)

    except KeyboardInterrupt:
        print("\n🛑 사용자 중단")
    finally:
        sensor_dht.exit()
        conn.close()
        print("🔒 DB 연결 종료")

# ===============================
if __name__ == "__main__":
    main()
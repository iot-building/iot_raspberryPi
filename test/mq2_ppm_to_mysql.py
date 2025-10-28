# /home/pi/iot_raspberryPi/test/mq2_ppm_to_mysql.py

import time, json, math, os
import board, busio, digitalio
from adafruit_mcp3xxx.mcp3008 import MCP3008, P0
from adafruit_mcp3xxx.analog_in import AnalogIn
import mysql.connector
from mysql.connector import Error

# ======= DB 설정 =======
DB = {
    "host": "192.168.14.74",       # MacBook IP
    "user": "sample",
    "password": "tnalsdlchlrhdi!",
    "database": "smartbuilding4"
}
DEVICE_ID = 2  # MQ-2 device_id
# ======================

# ======= 센서 설정 =======
VCC = 5.0                  # ADC 기준전압 (3.3V 기준)
RL_KOHM = 5.0              # MQ-2 모듈 로드저항(kΩ)
R0_PATH = "/home/pi/iot_raspberryPi/test/mq2_r0.json"
GAS_TYPE = "LPG"           # 측정할 가스 종류 ("LPG", "SMOKE", "H2" 등)
# =========================

# ======= 곡선 포인트 (데이터시트 참고, 예시값) =======
GAS_CURVE_POINTS = {
    "LPG":   [(200, 2.2), (10000, 0.1)],
    "SMOKE": [(100, 3.0), (10000, 0.2)],
    "H2":    [(200, 2.5), (10000, 0.15)],
}
# ===============================================


# ----- 함수들 -----
def load_r0(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"R0 파일 없음: {path}\n먼저 mq2_calibrate.py로 캘리브레이션하세요.")
    with open(path) as f:
        j = json.load(f)
    return j["R0_ohm"]

def rs_from_voltage(vout, vcc=VCC, rl_kohm=RL_KOHM):
    rl = rl_kohm * 1000.0
    if vout <= 0:
        return math.inf
    return rl * (vcc - vout) / vout

def ppm_from_ratio(ratio, gas="LPG"):
    # 1. 안전 처리
    if ratio <= 0:
        print(f"⚠️ Invalid ratio={ratio:.3f}, skipping calculation")
        return None

    # 2. 그래프 보정식
    curve_params = {
        "LPG":  {"x1": 200, "y1": 1.7, "x2": 10000, "y2": -0.38},
        "CH4":  {"x1": 200, "y1": 2.3, "x2": 10000, "y2": -0.45},
        "CO":   {"x1": 200, "y1": 2.3, "x2": 10000, "y2": -0.48}
    }
    p = curve_params[gas]

    X1, Y1 = math.log10(p["x1"]), p["y1"]
    X2, Y2 = math.log10(p["x2"]), p["y2"]
    m = (Y2 - Y1) / (X2 - X1)

    # 3. 안전한 log 계산
    X = (math.log10(ratio) - Y1) / m + X1
    return 10 ** X

def connect_db():
    try:
        c = mysql.connector.connect(**DB)
        if c.is_connected():
            print("✅ MySQL 연결 성공")
            return c
    except Error as e:
        print(f"❌ DB 연결 실패: {e}")
    return None
# ------------------

def main():
    # SPI 세팅
    spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)
    cs  = digitalio.DigitalInOut(board.D8)  # CE0 사용
    mcp = MCP3008(spi, cs)
    ain = AnalogIn(mcp, P0)  # MQ-2 AOUT → CH0

    R0 = load_r0(R0_PATH)
    print(f"🔧 R0 = {R0:,.0f} Ω, RL = {RL_KOHM}kΩ, Gas = {GAS_TYPE}")

    conn = connect_db()
    if not conn:
        print("DB 연결 실패로 종료합니다.")
        return
    cur = conn.cursor()

    print("🔥 MQ-2 ppm 측정/저장 시작 (5초 간격)")
    try:
        while True:
            vout = ain.voltage
            rs = rs_from_voltage(vout)
            ratio = rs / R0 if R0 > 0 else float("inf")
            ppm = ppm_from_ratio(ratio, gas=GAS_TYPE)

            print(f"Vout={vout:.3f}V | Rs/R0={ratio:.3f} | {GAS_TYPE} ≈ {ppm:.1f} ppm")

            cur.execute("""
                INSERT INTO environment_data (device_id, gas_level)
                VALUES (%s, %s)
            """, (DEVICE_ID, ppm))
            conn.commit()
            print("💾 DB 저장 완료\n")
            time.sleep(5)

    except KeyboardInterrupt:
        print("\n🛑 사용자 중단")
    finally:
        cur.close()
        conn.close()
        print("🔒 DB 연결 종료")

if __name__ == "__main__":
    main()
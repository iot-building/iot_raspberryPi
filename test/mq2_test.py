import time
import board, busio, digitalio
from adafruit_mcp3xxx.mcp3008 import MCP3008, P0   # ✅ MCP3008 그대로 사용
from adafruit_mcp3xxx.analog_in import AnalogIn
import mysql.connector
from mysql.connector import Error

DB_CONFIG = {
    "host": "192.168.14.74",
    "user": "sample",
    "password": "tnalsdlchlrhdi!",
    "database": "smartbuilding4"
}

DEVICE_ID = 2  # MQ-2 센서 ID

def connect_db():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        if conn.is_connected():
            print("✅ MySQL 연결 성공")
            return conn
    except Error as e:
        print(f"❌ DB 연결 실패: {e}")
        return None

# ✅ SPI & MCP3208(=MCP3008 인터페이스 동일)
spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)
cs = digitalio.DigitalInOut(board.D8)
mcp = MCP3008(spi, cs)   # ✅ 그대로 사용 가능
chan = AnalogIn(mcp, P0) # ✅ CH0 연결

def main():
    conn = connect_db()
    if not conn:
        print("DB 연결 불가. 종료합니다.")
        return

    cursor = conn.cursor()
    print("🔥 MQ-2 가스 데이터 수집 시작 (5초마다 업데이트)")

    try:
        while True:
            gas_voltage = chan.voltage
            print(f"💨 MQ-2 전압: {gas_voltage:.3f} V")

            sql = """
                INSERT INTO environment_data (device_id, gas_level)
                VALUES (%s, %s)
            """
            cursor.execute(sql, (DEVICE_ID, gas_voltage))
            conn.commit()
            print("💾 DB 저장 완료\n")
            time.sleep(5)

    except KeyboardInterrupt:
        print("\n🛑 사용자 중단")

    finally:
        cursor.close()
        conn.close()
        print("🔒 DB 연결 종료")

if __name__ == "__main__":
    main()
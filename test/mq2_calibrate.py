# /home/pi/iot_raspberryPi/test/mq2_calibrate.py
import time, json, math
import board, busio, digitalio
from adafruit_mcp3xxx.mcp3008 import MCP3008, P0
from adafruit_mcp3xxx.analog_in import AnalogIn

VCC = 3.3
RL_KOHM = 5.0
DURATION = 30
SAVE_PATH = "/home/pi/iot_raspberryPi/test/mq2_r0.json"

spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)
cs = digitalio.DigitalInOut(board.D8)
mcp = MCP3008(spi, cs)
ain = AnalogIn(mcp, P0)

def rs_from_voltage(vout, vcc=VCC, rl_kohm=RL_KOHM):
    rl = rl_kohm * 1000.0
    return rl * (vcc - vout) / vout if vout > 0 else math.inf

print("🌬️ 깨끗한 공기에서 30초간 캘리브레이션 시작...")
samples, rs_sum = 0, 0

start = time.time()
while time.time() - start < DURATION:
    v = ain.voltage
    rs = rs_from_voltage(v)
    rs_sum += rs
    samples += 1
    time.sleep(0.1)

rs_air = rs_sum / samples
R0 = rs_air / 9.8  # 데이터시트 기준 Clean Air 비율

with open(SAVE_PATH, "w") as f:
    json.dump({"R0_ohm": R0}, f, indent=2)
print(f"✅ 완료! R0 = {R0:,.0f} Ω → {SAVE_PATH}에 저장됨")
import RPi.GPIO as GPIO
import time
from threading import Thread

class ServoGate:
    def __init__(self, pin=18):
        self.pin = pin
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.OUT)

        # ✅ PWM 객체를 한 번만 생성해서 재사용
        self.pwm = GPIO.PWM(self.pin, 50)  # 50Hz 주파수
        self.pwm.start(0)
        print(f"✅ 서보모터 초기화 완료 (핀 {self.pin})")

    def set_angle(self, angle):
        """각도를 DutyCycle로 변환해 이동"""
        duty = 2.5 + (angle / 18)  # 0~180도 범위
        print(f"⚙️ 이동: {angle}° (Duty={duty:.2f})")
        self.pwm.ChangeDutyCycle(duty)
        time.sleep(1.5)  # 서보가 물리적으로 움직일 시간 확보
        self.pwm.ChangeDutyCycle(0)  # 떨림 방지

    def open_gate(self):
        print("🔓 차단기 열림")
        self.set_angle(90)
        print("✅ 열림 완료")

    def close_gate(self):
        print("🔒 차단기 닫힘")
        self.set_angle(0)
        print("✅ 닫힘 완료")

    def open_async(self):
        Thread(target=self.open_gate, daemon=True).start()

    def close_async(self):
        Thread(target=self.close_gate, daemon=True).start()

    def cleanup(self):
        self.pwm.stop()
        GPIO.cleanup(self.pin)
        print("🧹 서보모터 핀 정리 완료")

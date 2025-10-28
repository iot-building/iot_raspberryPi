import RPi.GPIO as GPIO
import time
from threading import Thread

class ServoGate:
    def __init__(self, pin=18):
        self.pin = pin
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.OUT)
        print(f"✅ 서보모터 핀 초기화 완료 (핀 {self.pin})")

    def _move(self, duty):
        """PWM을 매번 새로 생성해서 충돌 방지"""
        pwm = GPIO.PWM(self.pin, 50)
        pwm.start(0)
        pwm.ChangeDutyCycle(duty)
        time.sleep(1.2)
        pwm.ChangeDutyCycle(0)
        pwm.stop()

    def set_angle(self, angle):
        duty = 2.5 + (angle / 18)
        self._move(duty)

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
        GPIO.cleanup(self.pin)
        print("🧹 서보모터 핀 정리 완료")

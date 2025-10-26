import RPi.GPIO as gpio
import time

class LED_Device:
    def __init__(self,pin: int):
        self.type = "led"
        self.pin = pin #핀 번호
        self.current_state = False # on/off state
        self.brightness = 0 # 0-100 range 밝기 세기
        
        #GPIO 핀 세팅
        try:
            gpio.setmode(gpio.BCM)
            gpio.setup(self.pin,gpio.OUT)
            gpio.output(self.pin,gpio.LOW)
            self.pwm = gpio.PWM(self.pin, 100) #주파수 100Hz 설정
            print(f"LED 초기화 성공, 핀 번호: {self.pin}")
        except Exception as e:
            print(f"LED 초기화에 문제 발생: {e}")
    
    # LED의 상태 제어
    def set_power(self,state: bool):
        if state:
            self.current_state = True
            gpio.output(self.pin,gpio.HIGH)
        elif not state:
            self.current_state = False
            
            gpio.output(self.pin,gpio.LOW)
        
    # LED 밝기 조절
    def set_brightness(self,brightness: int = 100):
        """LED 밝기 설정 (0-100)"""
        try:
            # 밝기 값 범위 확인
            brightness = max(0, min(100, brightness))
            
            # PWM을 사용한 밝기 제어
            if not hasattr(self, 'pwm'):
                self.pwm = gpio.PWM(self.pin, 100)  # 100Hz 주파수
                self.pwm.start(0)
            
            self.pwm.ChangeDutyCycle(brightness)
            
            #밝기 조절을 0 이상으로 줬다는 건 on 상태라는 것
            self.brightness = brightness
            self.current_state = brightness > 0
            if self.current_state:
                print(f"LED 밝기 설정: {brightness}%")
                gpio.output(self.pin, gpio.HIGH)
            else:
                print(f"LED 꺼짐")
                gpio.output(self.pin, gpio.LOW)
            
        except Exception as e:
            print(f"LED 밝기 설정 실패: {e}")
            
    def get_type(self):
        """LED 타입 반환"""
        return self.type
    
    def get_state(self):
        """LED 현재 상태 반환"""
        return {
            "pin": self.pin,
            "state": self.current_state,
            "brightness": self.brightness
        }     
        
    def handle_mqtt_command(self, command):
        """MQTT 명령 처리"""
        action = command.get("action", "").lower()
        print(command, action)
        if action == "led_on":
            self.set_power(True)
            return False
        elif action == "led_off":
            self.set_power(False)
            return False
        elif action == "brightness":
            brightness = int(command.get("brightness"))
            self.set_brightness(brightness)
            return False
        elif action == "state_return":
            return self.get_state()
        else:
            print(f"알 수 없는 LED 명령: {action}")
            return False
    
    def clear(self):
        gpio.output(self.pin,gpio.LOW)
        
if __name__ == "__main__":
    led = LED_Device(23)
    led.set_power(True)
    print(led.get_state())
    time.sleep(1)
    led.set_brightness(50)
    print(led.get_state())
    time.sleep(1)
    led.set_power(False)
    print(led.get_state())
    
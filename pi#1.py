# Pi #1 (1층 + 주차장) | IP: 192.168.14.
# ┌─────────────────────────────┐
# │ LED 조명(1층)    Pin 23 PWM
# │ 서보모터(1층)    Pin 24 PWM
# │ DHT11 센서       Pin 25 1-Wire
# │
# │ [주차장]
# │ 초음파 TRIG      Pin 5 GPIO
# │ 초음파 ECHO      Pin 6 GPIO
# │ 서보모터         Pin 26 PWM
# └─────────────────────────────┘

from mqtt.mqtt_client import MqttClient
from device_manager import DeviceManager
from devices.dht import DHT_Device
from devices.led import LED_Device
from devices.elevator import Elevator
import time

def main():
    print("""
          # Pi #1 (1층 + 주차장) r4
# ┌─────────────────────────────┐
# │ LED 조명(1층)    Pin 23 PWM
# │ 서보모터(1층)    Pin 24 PWM
# │ DHT11 센서       Pin 25 1-Wire
# │
# │ [주차장]
# │ 초음파 TRIG      Pin 5 GPIO
# │ 초음파 ECHO      Pin 6 GPIO
# │ 서보모터         Pin 26 PWM
# └─────────────────────────────┘
          """)
    global mqtt, device_manager
    mqtt = MqttClient()
    device_manager = DeviceManager(mqtt)
    
    # 디바이스 초기화
    # LED 액추에이터
    led_pin = 23
    led_actuator = LED_Device(led_pin)
    device_manager.add_subscribe(str(led_pin), led_actuator)
    print("LED 액추에이터 초기화 완료")
    # 서보모터 ???
    servo_pin =24
    # 서보모터 생성자 생성
    # device_manager.add_subscribe() 추가
    
    # DHT 온습도 센서
    dht_pin = 25
    dht_sensor = DHT_Device(dht_pin)
    device_manager.add_publish(str(dht_pin), dht_sensor)
    print("DHT 센서 초기화 완료")
    
    elevator = Elevator()
    device_manager.add_subscribe("4",elevator)
    print("엘리베이터 초기화 완료")
    
def connect():
    #Mqtt 연결
    mqtt.connect()
    print("MQTT 브로커 서버 접속 시도")
    time.sleep(1)
    if not mqtt.connected:
        print("MQTT 연결실패")
        return False
    else:
        return True
    
def main_loop():
    """메인 실행 루프"""
    sensor_interval = 5.0  # 센서 데이터 수집 간격 (초)
    last_sensor_time = 0
    
    while True:
        current_time = time.time()
        
        # 센서 데이터 수집 및 발행
        if current_time - last_sensor_time >= sensor_interval:
            devices = device_manager.publish_list
            for device in devices.keys():
                device_manager.publish_data(device)
            last_sensor_time = current_time
        
        # MQTT 연결 상태 확인
        if not mqtt.connected:
            print("MQTT 연결 끊어짐 - 재연결 시도")
            try:
                mqtt.connect()
                time.sleep(1)
            except Exception as e:
                print(f"MQTT 재연결 실패: {e}")
        
        # 짧은 대기
        time.sleep(0.1)

def stop():
        print("IoT 시스템 중지")
        try:
            # 디바이스 정리
            if device_manager:
                device_manager.cleanup()

            # MQTT 연결 해제
            if mqtt:
                mqtt.disconnect()
        except Exception as e:
            print(f"시스템 중지 중 오류: {e}")
        finally:
            print("IoT 시스템 중지 완료")

if __name__ == "__main__":
    main()
    isConnected = connect()
    if isConnected:
        try:
            main_loop()
        except KeyboardInterrupt:
            print("\n시스템이 사용자에 의해 중단되었습니다.")
            stop()
        except Exception as e:
            print(f"시스템 오류: {e}")
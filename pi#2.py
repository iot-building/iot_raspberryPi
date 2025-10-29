# Pi #2 (2층.3층 + 화재경보) | IP: 192.168.14.
# ┌─────────────────────────────┐
# │ LED 조명(2층)    Pin 23 PWM
# │ 경보장치         Pin 22 PWM
# │ LED 조명(3층)    Pin 26 PWM
# │ 서보모터(2층)    Pin 24 PWM
# │ 화재센서(MQ-2)   Pin 27 INPUT
# │ 서보모터(3층)    Pin 4 PWM
# └─────────────────────────────┘

from mqtt.mqtt_client import MqttClient
from device_manager import DeviceManager
from devices.dht import DHT_Device
from devices.led import LED_Device
from devices.elevator import Elevator
import time

def main():
    print("IoT Raspberry Pi 시스템 시작")
    global mqtt, device_manager
    mqtt = MqttClient()
    # 해당 officeID 값 Mqtt 통신할 때 토픽으로 받는 값이
    # {office_id}/{device_type}{device_pin}/cmd
    # 여기서는 2층과 3층을 제어해야댐
    office_id = 1 
    device_manager = DeviceManager(mqtt,office_id)
    
    # 디바이스 초기화
    
    # DHT 온습도 센서 추가 (주로 publish)
    # dht_pin = 25
    # dht_sensor = DHT_Device(dht_pin)
    # device_manager.add_publish(str(dht_pin), dht_sensor)
    # print("DHT 센서 초기화 완료")
    
    # LED 액추에이터 추가 (주로 subscribe)
    led_pin1 = 23
    led_actuator1 = LED_Device(led_pin1)
    device_manager.add_subscribe(str(led_pin1), led_actuator1)
    print("LED 액추에이터 초기화 완료")
    led_pin2 = 26
    led_actuator2 = LED_Device(led_pin2)
    device_manager.add_subscribe(str(led_pin2), led_actuator2)
    print("LED 액추에이터 초기화 완료")
    
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
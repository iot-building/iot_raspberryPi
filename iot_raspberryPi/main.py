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
    device_manager = DeviceManager(mqtt)
    
    # 디바이스 초기화
    
    # DHT 온습도 센서 추가 (주로 publish)
    dht_pin = 25
    dht_sensor = DHT_Device(dht_pin)
    device_manager.add_publish(str(dht_pin), dht_sensor)
    print("DHT 센서 초기화 완료")
    
    # LED 액추에이터 추가 (주로 subscribe)
    led_pin = 23
    led_actuator = LED_Device(led_pin)
    device_manager.add_subscribe(str(led_pin), led_actuator)
    print("LED 액추에이터 초기화 완료")
    
    elevator = Elevator()
    device_manager.add_subscribe("ev1",elevator)
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
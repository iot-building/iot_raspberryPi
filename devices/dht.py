import time
import adafruit_dht
import board
import sys
import os

class DHT_Device:
    """DHT22 온습도 센서를 제어하는 클래스"""
    
    def __init__(self, pin: int):
        self.type = "dht"
        self.pin = getattr(board, f"D{pin}")
        self.sensor = adafruit_dht.DHT11(self.pin)
        print(f"DHT 초기화 성공, 핀 번호: {self.pin}")
        self.last_temperature = None
        self.last_humidity = None
    
    def handle_mqtt_state(self):
        """온도와 습도 데이터 읽기"""
        try:
            temperature = self.sensor.temperature
            humidity = self.sensor.humidity
            data = {
                "temperature": temperature,
                "humidity": humidity
            }
            self.last_temperature = temperature
            self.last_humidity = humidity
            
            print(f"센서 데이터: 온도 {temperature}°C, 습도 {humidity}%")
            return data
        
        except RuntimeError as err:
            print(err)
            print(f"이전 센서 데이터: 온도 {self.last_temperature}°C, 습도 {self.last_humidity}%")
            return {
                "temperature": self.last_temperature,
                "humidity": self.last_humidity
            }
    
    def get_type(self):
        return self.type
    
    def get_last_temperature(self):
        """마지막으로 읽은 온도 반환"""
        return self.last_temperature
    
    def get_last_humidity(self):
        """마지막으로 읽은 습도 반환"""
        return self.last_humidity
    
    def is_sensor_available(self) -> bool:
        """센서 사용 가능 여부 확인"""
        return self.sensor is not None
    
    def get_sensor_info(self):
        """센서 정보 반환"""
        return {
            "pin": self.pin,
            "available": self.is_sensor_available(),
            "last_temperature": self.last_temperature,
            "last_humidity": self.last_humidity,
        }

if __name__ == "__main__":
    pin = 25
    sensor = DHT_Device(pin)
    sensor.handle_mqtt_state()
    time.sleep(1)
    print(sensor.get_last_humidity())
    print(sensor.get_last_temperature())
    print(sensor.is_sensor_available())
    print(sensor.get_sensor_info())
    time.sleep(1)
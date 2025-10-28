import paho.mqtt.client as mqtt
import json
import time
import threading
import RPi.GPIO as gpio
import adafruit_dht
import board
import mysql.connector
import sys
import os



# ✅ 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_connect import DBManager



BROKER = "192.168.14.59"
PORT = 1883
CLIENT_ID = "SmartBuilding_Python"
TOPICS = ["office/+/fan", "office/+/led"]



led_device = None
fan_device = None
dht_device = None
mqtt_client = None



# ✅ 전역 변수로 DB 동기화 상태 관리
db_lock = threading.Lock()
pending_updates = {}  # {"device_name": "status"}




def init_gpio():
    try:
        gpio.setmode(gpio.BCM)
        gpio.setwarnings(False)
        
        # ✅ 모든 핀을 명시적으로 설정
        gpio.setup(23, gpio.OUT, initial=gpio.LOW)   # LED (LOW = 꺼짐)
        gpio.setup(17, gpio.OUT, initial=gpio.HIGH)  # FAN (HIGH = 꺼짐)
        
        print("✅ GPIO initialized")
    except Exception as e:
        print(f"❌ GPIO init error: {e}")


class LED_Device:
    def __init__(self, pin: int):
        self.type = "led"
        self.pin = pin
        self.device_name = "101A LED조명"
        self.current_state = False
        
        try:
            gpio.setup(self.pin, gpio.OUT, initial=gpio.LOW)
            self.pwm = gpio.PWM(self.pin, 100)
            self.pwm.start(0)
            print(f"✅ LED initialized on pin {self.pin}")
            
            # ✅ DB에 기기 정보 삽입
            db = DBManager()
            if db.conn and db.conn.is_connected():
                db.insert_data(
                    table="device",
                    data={
                        "room_id": 1,
                        "name": self.device_name,
                        "type": "LED",
                        "status": "OFF"
                    }
                )
            
        except Exception as e:
            print(f"❌ LED init error on pin {self.pin}: {e}")
    
    def set_power(self, state: bool):
        try:
            if state:
                self.current_state = True
                self.pwm.ChangeDutyCycle(100)
                gpio.output(self.pin, gpio.HIGH)
                print("✅ LED ON")
                with db_lock:
                    pending_updates["101A LED조명"] = "ON"
            else:
                self.current_state = False
                self.pwm.ChangeDutyCycle(0)
                gpio.output(self.pin, gpio.LOW)
                print("✅ LED OFF")
                with db_lock:
                    pending_updates["101A LED조명"] = "OFF"
        except Exception as e:
            print(f"❌ LED control error: {e}")
    
    def cleanup(self):
        try:
            self.pwm.stop()
            gpio.cleanup(self.pin)
        except Exception as e:
            print(f"LED cleanup error: {e}")




class FAN_Device:
    def __init__(self, pin: int):
        self.type = "fan"
        self.pin = pin
        self.device_name = "101A 쿨링팬"
        self.current_state = False
        
        try:
            gpio.setup(self.pin, gpio.OUT, initial=gpio.HIGH)  # ✅ HIGH로 초기화 (꺼짐)
            self.pwm = gpio.PWM(self.pin, 100)
            self.pwm.start(0)
            gpio.output(self.pin, gpio.HIGH)  # ✅ 안전하게 HIGH 설정 (꺼짐)
            print(f"✅ FAN initialized on pin {self.pin}")
            
            # ✅ DB에 기기 정보 삽입
            db = DBManager()
            if db.conn and db.conn.is_connected():
                db.insert_data(
                    table="device",
                    data={
                        "room_id": 1,
                        "name": self.device_name,
                        "type": "FAN",
                        "status": "OFF"
                    }
                )
            
        except Exception as e:
            print(f"❌ FAN init error on pin {self.pin}: {e}")
    
    def set_power(self, state: bool):
        try:
            if state:
                self.current_state = True
                gpio.output(self.pin, gpio.LOW)   # ✅ LOW에서 켜짐!
                print("✅ FAN ON")
                with db_lock:
                    pending_updates["101A 쿨링팬"] = "ON"
            else:
                self.current_state = False
                gpio.output(self.pin, gpio.HIGH)  # ✅ HIGH에서 꺼짐!
                print("✅ FAN OFF")
                with db_lock:
                    pending_updates["101A 쿨링팬"] = "OFF"
        except Exception as e:
            print(f"❌ FAN control error: {e}")
    
    def cleanup(self):
        try:
            self.pwm.stop()
            gpio.cleanup(self.pin)
        except Exception as e:
            print(f"FAN cleanup error: {e}")




class DHT_Device:
    def __init__(self, pin: int):
        self.type = "dht"
        self.device_name = "101A 온습도센서"
        
        try:
            self.pin = getattr(board, f"D{pin}")
            self.sensor = adafruit_dht.DHT11(self.pin)
            print(f"✅ DHT sensor initialized on D{pin}")
            
            # ✅ DB에 기기 정보 삽입
            db = DBManager()
            if db.conn and db.conn.is_connected():
                db.insert_data(
                    table="device",
                    data={
                        "room_id": 1,
                        "name": self.device_name,
                        "type": "DHT11",
                        "status": "정상"
                    }
                )
            
        except Exception as e:
            print(f"❌ DHT init error: {e}")
            self.sensor = None
        
        self.last_temperature = None
        self.last_humidity = None
    
    def read_data(self):
        try:
            if self.sensor is None:
                return {"temperature": self.last_temperature, "humidity": self.last_humidity}
            
            temperature = self.sensor.temperature
            humidity = self.sensor.humidity
            if temperature is not None and humidity is not None:
                self.last_temperature = temperature
                self.last_humidity = humidity
                print(f"📊 DHT: {temperature}°C, {humidity}%")
                return {"temperature": temperature, "humidity": humidity}
        except Exception as e:
            print(f"❌ DHT read error: {e}")
        
        return {"temperature": self.last_temperature, "humidity": self.last_humidity}




def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ MQTT connected")
        for topic in TOPICS:
            client.subscribe(topic, qos=1)
            print(f"📢 Subscribed to: {topic}")
    else:
        print(f"❌ MQTT connection failed with code: {rc}")




def on_disconnect(client, userdata, rc):
    if rc != 0:
        print(f"⚠️ MQTT disconnected unexpectedly: {rc}")
    else:
        print("ℹ️ MQTT disconnected")




def on_message(client, userdata, msg):
    global led_device, fan_device
    topic = msg.topic
    payload = msg.payload.decode()
    print(f"📨 Message received from {topic}: {payload}")
    try:
        data = json.loads(payload)
        action = data.get("action", "").upper()
        
        if "led" in topic:
            if action == "ON":
                led_device.set_power(True)
            elif action == "OFF":
                led_device.set_power(False)
        elif "fan" in topic:
            if action == "ON":
                fan_device.set_power(True)
            elif action == "OFF":
                fan_device.set_power(False)
    except Exception as e:
        print(f"❌ Message processing error: {e}")




def initialize_mqtt():
    global mqtt_client
    try:
        mqtt_client = mqtt.Client(CLIENT_ID)
        mqtt_client.on_connect = on_connect
        mqtt_client.on_disconnect = on_disconnect
        mqtt_client.on_message = on_message
        mqtt_client.reconnect_delay_set(min_delay=1, max_delay=10)
        mqtt_client.connect(BROKER, PORT, keepalive=60)
        mqtt_client.loop_start()
        print(f"✅ MQTT connection initiated to {BROKER}:{PORT}")
        return True
    except Exception as e:
        print(f"❌ MQTT init error: {e}")
        return False




# ✅ DB 업데이트 함수
def update_db():
    global pending_updates
    while True:
        try:
            time.sleep(10)
            
            with db_lock:
                if not pending_updates:
                    updates_to_apply = {}
                else:
                    updates_to_apply = pending_updates.copy()
                    pending_updates.clear()
            
            db = DBManager()
            
            if not db.conn or not db.conn.is_connected():
                continue
            
            # ✅ LED 업데이트
            if "101A LED조명" in updates_to_apply:
                db.update_data(
                    table="device",
                    data={"status": updates_to_apply["101A LED조명"]},
                    where={"name": "101A LED조명"}
                )
                print(f"✅ DB 업데이트: 101A LED조명 → {updates_to_apply['101A LED조명']}")
            
            # ✅ FAN 업데이트
            if "101A 쿨링팬" in updates_to_apply:
                db.update_data(
                    table="device",
                    data={"status": updates_to_apply["101A 쿨링팬"]},
                    where={"name": "101A 쿨링팬"}
                )
                print(f"✅ DB 업데이트: 101A 쿨링팬 → {updates_to_apply['101A 쿨링팬']}")
            
            # ✅ DHT 센서 데이터 항상 업데이트
            if dht_device and dht_device.sensor:
                dht_data = dht_device.read_data()
                if dht_data["temperature"] is not None and dht_data["humidity"] is not None:
                    db.update_data(
                        table="device",
                        data={"status": f"{dht_data['temperature']}°C, {dht_data['humidity']}%"},
                        where={"name": "101A 온습도센서"}
                    )
            
        except Exception as e:
            print(f"❌ DB error: {e}")




if __name__ == "__main__":
    try:
        init_gpio()
        
        led_device = LED_Device(pin=23)
        fan_device = FAN_Device(pin=17)
        dht_device = DHT_Device(pin=25)
        
        if not initialize_mqtt():
            print("⚠️ MQTT initialization failed, but continuing...")
        
        db_thread = threading.Thread(target=update_db, daemon=True)
        db_thread.start()
        
        print("✅ System ready")
        while True:
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        if mqtt_client:
            mqtt_client.loop_stop()
            mqtt_client.disconnect()
        if led_device:
            led_device.cleanup()
        if fan_device:
            fan_device.cleanup()
        print("✅ Cleanup completed")
    
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
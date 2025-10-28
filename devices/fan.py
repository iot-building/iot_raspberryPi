import paho.mqtt.client as mqtt
import json
import time
import threading
import RPi.GPIO as gpio
import adafruit_dht
import board
import mysql.connector

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
        print("✅ GPIO initialized")
    except Exception as e:
        print(f"❌ GPIO init error: {e}")


class LED_Device:
    def __init__(self, pin: int):
        self.type = "led"
        self.pin = pin
        self.current_state = False
        try:
            gpio.setup(self.pin, gpio.OUT, initial=gpio.LOW)
            self.pwm = gpio.PWM(self.pin, 100)
            self.pwm.start(0)
            print(f"✅ LED initialized on pin {self.pin}")
        except Exception as e:
            print(f"❌ LED init error on pin {self.pin}: {e}")
    
    def set_power(self, state: bool):
        try:
            if state:
                self.current_state = True
                self.pwm.ChangeDutyCycle(100)
                print("✅ LED ON")
                # ✅ 상 태 변경 후 즉시 DB 업데이트 표시
                with db_lock:
                    pending_updates["101A LED조명"] = "ON"
            else:
                self.current_state = False
                self.pwm.ChangeDutyCycle(0)
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
        self.current_state = False
        try:
            gpio.setup(self.pin, gpio.OUT, initial=gpio.LOW)
            self.pwm = gpio.PWM(self.pin, 100)
            self.pwm.start(0)
            print(f"✅ FAN initialized on pin {self.pin}")
        except Exception as e:
            print(f"❌ FAN init error on pin {self.pin}: {e}")
    
    def set_power(self, state: bool):
        try:
            if state:
                self.current_state = True
                self.pwm.ChangeDutyCycle(100)
                print("✅ FAN ON")
                # ✅ 상태 변경 후 즉시 DB 업데이트 표시
                with db_lock:
                    pending_updates["101A 쿨링팬"] = "ON"
            else:
                self.current_state = False
                self.pwm.ChangeDutyCycle(0)
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
        try:
            self.pin = getattr(board, f"D{pin}")
            self.sensor = adafruit_dht.DHT11(self.pin)
            print(f"✅ DHT sensor initialized on D{pin}")
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


# ✅ 개선된 DB 업데이트 함수
def update_db():
    global pending_updates
    while True:
        try:
            time.sleep(10)  # ✅ 10초마다 확인 (더 자주!)
            
            with db_lock:
                if not pending_updates:
                    # pending 업데이트가 없으면 주기적으로 센서 데이터만 업데이트
                    updates_to_apply = {}
                else:
                    # pending 업데이트가 있으면 그것과 센서 데이터 모두 업데이트
                    updates_to_apply = pending_updates.copy()
                    pending_updates.clear()
            
            conn = mysql.connector.connect(
                host="127.0.0.1",
                user="sample",
                password="1234",
                database="kkm"
            )
            cursor = conn.cursor()
            
            # ✅ pending 업데이트 먼저 적용
            if "101A LED조명" in updates_to_apply:
                cursor.execute(
                    "UPDATE device SET status=%s WHERE name = '101A LED조명'",
                    (updates_to_apply["101A LED조명"],)
                )
                print(f"✅ DB 업데이트: 101A LED조명 → {updates_to_apply['101A LED조명']}")
            
            if "101A 쿨링팬" in updates_to_apply:
                cursor.execute(
                    "UPDATE device SET status=%s WHERE name = '101A 쿨링팬'",
                    (updates_to_apply["101A 쿨링팬"],)
                )
                print(f"✅ DB 업데이트: 101A 쿨링팬 → {updates_to_apply['101A 쿨링팬']}")
            
            # ✅ DHT 센서 데이터 항상 업데이트
            dht_data = dht_device.read_data()
            if dht_data["temperature"]:
                cursor.execute(
                    "UPDATE device SET status=%s WHERE name = '101A 온도센서'",
                    (f"{dht_data['temperature']}°C",)
                )
            if dht_data["humidity"]:
                cursor.execute(
                    "UPDATE device SET status=%s WHERE name = '101A 습도센서'",
                    (f"{dht_data['humidity']}%",)
                )
            
            conn.commit()
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"❌ DB error: {e}")


if __name__ == "__main__":
    try:
        init_gpio()
        
        led_device = LED_Device(pin=23)
        fan_device = FAN_Device(pin=24)
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

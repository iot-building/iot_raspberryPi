import time
import os
from dotenv import load_dotenv
import paho.mqtt.client as mqtt
from threading import Thread

class MqttClient:
    # 브로커 서버 값 할당 (ip,port,id)
    def __init__(self,client_id: str = "raspberry_pi"):
        env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
        load_dotenv(dotenv_path=env_path)
        
        self.broker_host = os.getenv("BROKER_HOST")
        self.broker_port = int(os.getenv("BROKER_PORT")) # 포트는 정수형
        self.client_id = client_id
        self.client = None
        self.connected = False
        
        # 콜백 함수들
        self.on_message_callback = None
        self.on_connect_callback = None
        self.on_disconnect_callback = None
    
    ###### 브로커 서버 연결, 연결 콜백함수 #####
    
    # 브로커 서버 연결
    def connect(self):
        self.client = mqtt.Client(client_id=self.client_id)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
        self.client.connect(self.broker_host, self.broker_port, 60)
        mqtt_obj = Thread(target=self.client.loop_forever)
        mqtt_obj.start()
        print(f"MQTT 클라이언트 연결 시도: {self.broker_host}:{self.broker_port}")
    # MQTT 연결 콜백 (connect() 메서드 실행되면 자동 콜백되는 메서드)
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            print("MQTT 브로커 연결 성공")
            if self.on_connect_callback:
                self.on_connect_callback()
        else:
            self.connected = False
            print(f"MQTT 브로커 연결 실패: {rc}")
    # device_manager에서 on_connect_callback 메서드를 할당
    # connect() 실행 시 할당된 메서드도 실행되도록
    def set_on_connect_callback(self, callback):
        self.on_connect_callback = callback
        
    #########################################
    
    # subscribe 메시지 콜백
    def on_message(self, client, userdata, msg):
        topic = msg.topic
        value = msg.payload.decode("utf-8")
        print(topic + "===========" + value)
        if self.on_message_callback:
            self.on_message_callback(topic,value)
        
    def set_on_message_callback(self, callback):
        """메시지 수신 콜백 함수 설정"""
        self.on_message_callback = callback
        
    def subscribe(self, topic: str, qos: int = 1):
        """토픽 구독"""
        if not self.connected:
            print("MQTT 연결되지 않음. 구독 실패")
            return False
        self.client.subscribe(topic, qos)
    
    def publish(self, topic, payload: dict, qos:int = 1):
        """토픽에 메시지 발행"""
        if not self.connected:
            print("MQTT 연결되지 않음. 메시지 발행 실패")
            return False
        message = str(payload)
        self.client.publish(topic,message, qos=qos)
            
    def disconnect(self):
        """MQTT 브로커 연결 해제"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False
            print("MQTT 연결 해제")
    
    # MqttClient 객체의 상태 정보 반환
    def get_state(self):
        """MQTT 현재 상태 반환"""
        return {
            "client_id": self.client_id,
            "connected": self.connected,
        }     

if __name__ == "__main__":
    mqtt_obj = MqttClient()
    time.sleep(1)
    mqtt_obj.connect()
    time.sleep(1)
    mqtt_obj.subscribe("1/led/23/cmd",0)
    time.sleep(2)
    mqtt_obj.publish("1/led/23/cmd",{"control":"led_on"})
    time.sleep(1)
    print(mqtt_obj.get_state())
    mqtt_obj.disconnect()
    time.sleep(1)
    print(mqtt_obj.get_state())
    
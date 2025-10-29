from mqtt.mqtt_client import MqttClient
from devices.led import LED_Device
from devices.dht import DHT_Device
import time
import json

class DeviceManager:
    def __init__(self,client: MqttClient, office_id):
        self.office_id = office_id # 보드 별로 층으로 구분해서 동작할 때 변경
        self.client = client
        self.devices = {}
        self.subscribe_list = {} # subscribe 해야할 디바이스들 여기에
        self.publish_list = {} # publish 통신하는 디바이스들 여기에
        
        # MQTT 콜백 설정
        # 자바에서 publish 들어오면 _handle_mqtt_message 메서드가 실행됨
        self.client.set_on_message_callback(self._handle_mqtt_message)
        # mqtt_client로 브로커 서버랑 연결하면 _on_mqtt_connect 메서드가 실행됨
        self.client.set_on_connect_callback(self._on_mqtt_connect)
        
    # publish 관련 로직 처리
    def add_publish(self,pub_id: str, device):
        self.devices[pub_id] = device
        self.publish_list[pub_id] = device
    
    def publish_data(self,device_id,data = None, action = "state"):
        # publish 토픽, 메시지(payload)으로 데이터 전송
        # publish topic 구조: {officeId}/{decive_type}/{device_id}/state
        device = self.devices[device_id]
        topic = f"{self.office_id}/{device.get_type()}/{device_id}/{action}"
        if data is None:
            data = device.handle_mqtt_state()
        self.client.publish(topic,data)
        print(f"센서 데이터 발행 완료: {topic}")
        print(f"발행 데이터: {data}")
        return True
    
    # subscribe 관련 로직 처리
    def add_subscribe(self,sub_id: str, device):
        self.subscribe_list[sub_id] = device
        self.devices[sub_id] = device
        # device 객체에 set_manager 메소드가 있는지 확인하고, 있다면 호출
        if hasattr(device, 'set_manager'):
            print("set_manager")
            device.set_manager(self,sub_id)
    
    def control_subscribe(self, target, command):
        """subscribe 토픽들 처리"""
        actuator = target
        # 각 액추에이터 마다 handel_mqtt_command 메서드를 세팅해야한다.
        if hasattr(actuator, 'handle_mqtt_command'):
            hasReturn = actuator.handle_mqtt_command(command)
        else:
            print(f"액추에이터 제어 메서드가 없음")
            return False
    
    def _handle_mqtt_message(self, topic: str, payload):
        """MQTT 메시지 처리"""
        """subscribe로 받은 메시지를 처리"""
        print(f"MQTT 메시지 수신: {topic} -> {payload}")
        
        msg = json.loads(payload)
        print(msg)
        # 토픽 파싱 예시
        # {office_id}/{device_type}/{device_id}/cmd
        topic_parts = topic.split('/')
        
        if len(topic_parts) >= 3:
            office_id = topic_parts[0]
            device_type = topic_parts[1]
            device_id = topic_parts[2]
            for sub_id, sub_obj in self.subscribe_list.items():
                # device_type이 동일한 디바이스를 찾기
                if sub_obj.type == device_type:
                    if sub_id == device_id:
                        self.control_subscribe(sub_obj,msg)
            else:
                print(f"알 수 없는 액추에이터: {device_id}")
        #토픽 구분 문구가 2개 이하면 잘못된 토픽 형식 
        else:
            print(f"잘못된 토픽 형식: {topic}")
    
    def _on_mqtt_connect(self):
        # connection 이후 subscribe 토픽 구독
        for sub_id, sub_obj in self.subscribe_list.items():
            topic = f"{self.office_id}/{sub_obj.get_type()}/{sub_id}/cmd"
            print(f"토픽 구독: {topic}")
            self.client.subscribe(topic,1)
            
    # DeviceManager 리소스 정리
    def cleanup(self):
        try:
            for device in self.subscribe_list.values():
                device.clear()
            self.devices.clear()
            self.publish_list.clear()
            self.subscribe_list.clear()
            
            print("모든 디바이스 리소스 정리 완료")
            
        except Exception as e:
            print(f"디바이스 정리 중 오류: {e}")
            
# DeviceManager 클래스 메서드들 동작 잘 되나 임시 테스트하는거
if __name__=="__main__":
    dm = DeviceManager(MqttClient())
    dm.add_subscribe("23",LED_Device(23)) #pin_23 조명센서 추가
    time.sleep(1)
    dm.add_publish("25",DHT_Device(25)) #pin_25 온습도센서 추가
    dm.client.connect()
    time.sleep(1)
    dm.publish_data("25")
    time.sleep(1)
    dm.control_subscribe("23",{"action": "led_on"})
    time.sleep(1)
    dm.cleanup()
    
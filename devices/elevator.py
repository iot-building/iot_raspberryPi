#!/usr/bin/python3
import RPi.GPIO as GPIO
import time

# defining stepper motor sequence (found in documentation http://www.4tronix.co.uk/arduino/Stepper-Motors.php)
global step_sequence
step_sequence = [[1,1,0,0], # IN1, IN2 On
                 [0,1,1,0], # IN2, IN3 On
                 [0,0,1,1], # IN3, IN4 On
                 [1,0,0,1]] # IN4, IN1 On
# Full Step은 4단계이므로, 모터 회전 루프의 % 8을 % 4로 변경해야 합니다.

class Elevator:
    #엘리베이터는 스탭 모터를 기반으로 움직인다.
    #스탭 모터는 회전 수에 따라 움직이는 거리가 결정되고, 층마다 해당 거리를 정해야한다.
     
    # 엘리베이터 관련 변수 초기화
    def __init__(self):
        self.in1 = 12
        self.in2 = 16
        self.in3 = 20
        self.in4 = 21
        self.motor_pins = [self.in1, self.in2, self.in3, self.in4]
        self.interval = 0.002
        self.type = "elevator"
        self.last_floor = 1
        self.state = True
        self.initialize()
        
    def initialize(self):
        GPIO.setmode( GPIO.BCM )
        for pin in self.motor_pins:
            GPIO.setup(pin,GPIO.OUT)
        # initializing
        for pin in self.motor_pins:
            GPIO.output(pin,GPIO.LOW)
        
    def turn(self,count,direction = False): # default : 시계 방향
        motor_step_counter = 0
        for i in range(int(count*4)):
            for pin in range(0, len(self.motor_pins)):
                GPIO.output(self.motor_pins[pin], step_sequence[motor_step_counter][pin] )
            time.sleep(self.interval)
            if direction==True: # 반시계 회전, 층 올라가는 로직
                motor_step_counter = (motor_step_counter - 1) % 4
            elif direction==False: # 시계 회전, 층 내려가는 로직
                motor_step_counter = (motor_step_counter + 1) % 4

    def turnDegrees(self,count,direction=False):
		# Turn n degrees
        self.turn(round(count*512/360,0),direction)
    
    # 모터 한바퀴를 도는 걸 1층으로 판단(임의코드)
    # start는 항상 self.last_floor 가 되고, end는 사용자가 이용하려는 층이 된다.
    # end 값은 1-3 범위에 있어야 한다.
    def turnFloors(self,start,end):
        if end < 1 or end > 3:
            print("1-3 층만 이용 가능합니다.")
            return False
        count = end - start
        if count == 0: #동일 층이면 동작 X
            print("입력한 층은 현재 층입니다.")
            return False   
        elif count > 0: # ex. start: 1 -> end: 3
            direction = True # 층을 올라가는 방향으로 회전
        else: # ex. start: 3 -> end: 2
            direction = False # 층을 내려가는 방향으로 회전
            count = -count
        self.turnDegrees(360*count,direction)
        self.last_floor = end
        return True
        
    def clear(self):
        self.turnFloors(self.last_floor, 1)
        GPIO.cleanup()
    
    def get_type(self): # 토픽을 생성하기 위함
        return self.type 
    
    def set_manager(self, manager, id):
        self.manager = manager
        self.device_id = id
    
    def publish_state(self, action: str, start, end=None):
        """엘리베이터의 현재 상태를 MQTT로 발행합니다."""
        if self.manager and self.device_id:
            # 발행할 데이터 생성
            data = {
                "from_floor": start,
                "to_floor" : end,
                "action": action
                }
            # DeviceManager의 publish_data 메소드 호출
            self.manager.publish_data(self.device_id, data)
    
    def handle_mqtt_command(self, command):
        """JAVA에서 들어온 MQTT 명령 처리"""
        action = command.get("action", "").lower() # {"action": "call"} 데이터일 경우 action = "call"
        if action == "call": # 엘리베이터 제어 (층 이동)
            if self.state is False:
                print("엘리베이터를 현재 이용할 수 없습니다.")
                return False
            start_floor = int(command.get("start_floor"))
            end_floor = int(command.get("end_floor"))
            self.call_and_arrive(start_floor,end_floor)
        elif action == "state_return": # 엘리베이터의 현재 상태를 요청하는 Mqtt 통신
            result = "enable" if self.state == True else "disable"
            self.publish_state(result, self.last_floor)
        elif action == "state_change":
            self.state = bool(command.get("state"))
            result = "enable" if self.state == True else "disable"
            print("엘리베이터 상태 변경: ", result)
        else:
            print(f"알 수 없는 E/V 명령: {action}")
            return False
    def call_and_arrive(self,start,end):
        #원래 엘리베이터 층 -> start 층 이동
        if self.turnFloors(self.last_floor,start):
            self.publish_state("call", start, end)
            # 이제 Mqtt로 Java에 안보내고, MySQL DB에 로그 형태로 저장할거임.
        print(f"{start}층에 도착했습니다.")
        print("문이 열립니다.")
        time.sleep(3) 
        print("문이 닫힙니다.")
        # start 층 -> end 층 이동
        if self.turnFloors(self.last_floor,end):
            self.publish_state("arrive",start,end)
            # 이제 Mqtt로 Java에 안보내고, MySQL DB에 로그 형태로 저장할거임.
        print(f"{end}층에 도착완료")

# the meat
if __name__ == "__main__":
    try:
        ev = Elevator()
        print("1층 -> 3층 이동")
        ev.turnFloors(1,3)
        time.sleep(1)
        ev.clear()

    except KeyboardInterrupt:
        ev.clear()
        exit( 1 )
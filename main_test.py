from mqtt_client1 import client, BROKER, PORT

if __name__ == "__main__":
    print("🚀 스마트 주차장 센서 시스템 실행 중...")
    client.connect(BROKER, PORT, 60)
    client.loop_forever()

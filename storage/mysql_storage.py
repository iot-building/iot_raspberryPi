import mysql.connector
from mysql.connector import Error

class MySQLStorage:
    def __init__(self, host='192.168.14.74', user='sample', password='tnalsdlchlrhdi!!', database='smartbuilding4'):
        try:
            self.conn = mysql.connector.connect(
                host=host,
                user=user,
                password=password,
                database=database
            )
            self.cursor = self.conn.cursor()
            print("✅ MySQL 연결 성공")
        except Error as e:
            print(f"❌ DB 연결 실패: {e}")
            self.conn = None

    def insert_environment_data(self, device_id, temperature=None, humidity=None, gas_level=None):
        """환경 센서 데이터 저장"""
        if not self.conn:
            print("DB 연결이 설정되지 않았습니다.")
            return
        try:
            sql = """
                INSERT INTO environment_data (device_id, temperature, humidity, gas_level)
                VALUES (%s, %s, %s, %s)
            """
            self.cursor.execute(sql, (device_id, temperature, humidity, gas_level))
            self.conn.commit()
            print(f"💾 DB 저장 완료 → device_id={device_id}, T={temperature}, H={humidity}, G={gas_level}")
        except Error as e:
            print(f"DB 저장 실패: {e}")

    def close(self):
        if self.conn:
            self.cursor.close()
            self.conn.close()
            print("🔒 DB 연결 종료")
 
if __name__ == "__main__":
        print("🔍 MySQL 연결 테스트 시작")
        db = MySQLStorage(
            host="192.168.14.74",          # 또는 Mac의 IP 주소 (예: 192.168.14.82)
            user="sample",             # MySQL 사용자명
            password="tnalsdlchlrhdi!", # MySQL 비밀번호
            database="smartbuilding4"
        )
        db.close()                     
    
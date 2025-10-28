import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

# ===============================
# DB 클래스 설정
# ===============================
class DBManager:
    """
    데이터베이스 연결 및 CRUD 작업을 관리하는 클래스
    """
    def __init__(self):
        """
        클래스 인스턴스 생성 시 .env 파일에서 환경 변수를 로드하고 DB에 연결합니다.
        """
        load_dotenv()
        db_config = {
            "host": os.getenv("DB_HOST"),
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD"),
            "database": os.getenv("DB_DATABASE")
        }
        
        self.conn = None
        try:
            self.conn = mysql.connector.connect(**db_config)
            if self.conn.is_connected():
                print("✅ DB 연결 성공")
        except Error as e:
            print(f"❌ DB 연결 실패: {e}")

    def __del__(self):
        """
        클래스 인스턴스 소멸 시 DB 연결을 자동으로 닫습니다.
        """
        if self.conn and self.conn.is_connected():
            self.conn.close()
            print("🔗 DB 연결 해제")

    # ===============================
    # 범용 CRUD 메서드
    # ===============================
    def insert_data(self, table, data):
        """
        지정된 테이블에 데이터를 삽입합니다.
        :param table: 테이블 이름 (str)
        :param data: 삽입할 데이터 {'컬럼명': 값} (dict)
        """
        if not self.conn or not self.conn.is_connected():
            print("❌ DB에 연결되어 있지 않습니다.")
            return

        columns = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        
        cur = self.conn.cursor()
        try:
            cur.execute(sql, list(data.values()))
            self.conn.commit()
            print(f"✅ [{table}] 데이터 삽입 성공")
        except Error as e:
            print(f"❌ [{table}] 데이터 삽입 실패: {e}")
        finally:
            cur.close()

    def select_data(self, table, columns="*", where=None):
        """
        지정된 테이블에서 데이터를 조회합니다.
        :param table: 조회할 테이블 이름 (str)
        :param columns: 조회할 컬럼 (str, 기본값: '*')
        :param where: WHERE 조건 {'컬럼명': 값} (dict, optional)
        :return: 조회 결과 (list of dicts)
        """
        if not self.conn or not self.conn.is_connected():
            print("❌ DB에 연결되어 있지 않습니다.")
            return []

        sql = f"SELECT {columns} FROM {table}"
        params = []
        if where:
            where_clauses = [f"{key} = %s" for key in where.keys()]
            sql += " WHERE " + " AND ".join(where_clauses)
            params = list(where.values())
            
        cur = self.conn.cursor(dictionary=True) # 결과를 딕셔너리로 받기
        results = []
        try:
            cur.execute(sql, params)
            results = cur.fetchall()
        except Error as e:
            print(f"❌ [{table}] 데이터 조회 실패: {e}")
        finally:
            cur.close()
        return results

    def update_data(self, table, data, where):
        """
        지정된 테이블의 데이터를 수정합니다.
        :param data: 수정할 데이터 {'컬럼명': 새 값} (dict)
        :param where: WHERE 조건 {'컬럼명': 값} (dict)
        """
        if not self.conn or not self.conn.is_connected():
            print("❌ DB에 연결되어 있지 않습니다.")
            return

        set_clauses = ', '.join([f"{key} = %s" for key in data.keys()])
        where_clauses = ' AND '.join([f"{key} = %s" for key in where.keys()])
        sql = f"UPDATE {table} SET {set_clauses} WHERE {where_clauses}"
        
        params = list(data.values()) + list(where.values())
        
        cur = self.conn.cursor()
        try:
            cur.execute(sql, params)
            self.conn.commit()
            print(f"🔄 [{table}] 데이터 수정 성공 (조건: {where})")
        except Error as e:
            print(f"❌ [{table}] 데이터 수정 실패: {e}")
        finally:
            cur.close()

    def delete_data(self, table, where):
        """
        지정된 테이블의 데이터를 삭제합니다.
        :param where: WHERE 조건 {'컬럼명': 값} (dict)
        """
        if not self.conn or not self.conn.is_connected():
            print("❌ DB에 연결되어 있지 않습니다.")
            return

        where_clauses = ' AND '.join([f"{key} = %s" for key in where.keys()])
        sql = f"DELETE FROM {table} WHERE {where_clauses}"
        
        cur = self.conn.cursor()
        try:
            cur.execute(sql, list(where.values()))
            self.conn.commit()
            print(f"🗑️ [{table}] 데이터 삭제 성공 (조건: {where})")
        except Error as e:
            print(f"❌ [{table}] 데이터 삭제 실패: {e}")
        finally:
            cur.close()
            
# ===============================
# DB 조작 함수
# ===============================
def insert_environment(conn, device_id, temp=None, hum=None, gas=None):
    sql = """
        INSERT INTO environment_data (device_id, temperature, humidity, gas_level)
        VALUES (%s, %s, %s, %s)
    """
    cur = conn.cursor()
    cur.execute(sql, (device_id, temp, hum, gas))
    conn.commit()
    cur.close()

def insert_event(conn, device_id, office_id, etype, action, value, note):
    sql = """
        INSERT INTO event_log (device_id, user_id, office_id, event_type, event_action, value, note)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    cur = conn.cursor()
    cur.execute(sql, (device_id, USER_ID, office_id, etype, action, value, note))
    conn.commit()
    cur.close()
    print(f"🚨 EVENT_LOG → [{etype}] {action} ({note})")

def update_device_status(conn, device_id, new_status):
    sql = "UPDATE devices SET status=%s, last_updated=NOW() WHERE device_id=%s"
    cur = conn.cursor()
    cur.execute(sql, (new_status, device_id))
    conn.commit()
    cur.close()
    print(f"🔄 DEVICE 상태 변경 → id={device_id}, status={new_status}")


# ===============================
# 메인 테스트 예시
# ===============================
if __name__ == '__main__':
    # DatabaseManager 클래스의 인스턴스를 생성합니다.
    # 이 시점에 자동으로 __init__ 메서드가 실행되어 DB에 연결됩니다.
    db = DBManager()

    # DB 연결이 성공했는지 확인
    if not db.conn or not db.conn.is_connected():
        print("DB 작업을 수행할 수 없습니다.")
        exit()

    # 1. 데이터 삽입 (INSERT)
    # print("\n--- 1. 데이터 삽입 예시 ---")
    # new_device = {
    #     "device_id": "SEN003",
    #     "device_name": "거실 온도 센서",
    #     "type": "Sensor",
    #     "status": "active"
    # }
    # db.insert_data(table="devices", data= new_device)

    # 2. 데이터 조회 (SELECT)
    print("\n--- 2. 데이터 조회 예시 ---")
    # 'Sensor' 타입의 모든 장비 조회
    sensors = db.select_data(table="devices", where={"type": "LED"})
    print("조회된 센서 목록:")
    for sensor in sensors:
        print(f"  - ID: {sensor['device_id']}, 이름: {sensor['name']}, 상태: {sensor['status']}")

    # 3. 데이터 수정 (UPDATE)
    # print("\n--- 3. 데이터 수정 예시 ---")
    # db.update_data(
    #     table="devices",
    #     data={"status": "inactive"},
    #     where={"device_id": "SEN003"}
    # )
    # # 수정 결과 확인
    # updated_sensor = db.select_data(table="devices", where={"device_id": "SEN003"})
    # print("수정된 센서 정보:", updated_sensor)

    # 4. 데이터 삭제 (DELETE)
    # print("\n--- 4. 데이터 삭제 예시 ---")
    # db.delete_data(table="devices", where={"device_id": "SEN003"})
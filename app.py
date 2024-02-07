import time
from flask import Flask, render_template, jsonify, Response
import Adafruit_DHT
import MySQLdb
import threading
import cv2

app = Flask(__name__)

cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
face_cascade = cv2.CascadeClassifier(cascade_path)

cam = cv2.VideoCapture(0)
cam.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)

def detect_objects(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

    for (x, y, w, h) in faces:
        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

    return frame

def generate():
    while True:
        ret, frame = cam.read()
        if not ret:
            break

        frame = detect_objects(frame)

        # Encode frame to JPEG format
        ret, jpegdata = cv2.imencode(".jpeg", frame)
        if not ret:
            break

        # Convert JPEG data to bytes
        jpegbytes = jpegdata.tobytes()

        boundary = "--MjpgBound"
        content_type = "Content-Type: image/jpeg"
        content_length = "Content-Length: " + str(len(jpegbytes))

        string = boundary + "\r\n"
        string += content_type + "\r\n"
        string += content_length + "\r\n\r\n"

        yield (string.encode("utf-8") + jpegbytes + b"\r\n\r\n")

@app.route('/stream')
def do_stream():
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=MjpgBound')

@app.route('/camera')
def do_route():
    return '<html><body><img src="stream" width=320 height=240></body></html>'


# MySQL 데이터베이스 연결 설정
db = MySQLdb.connect(
    host="localhost",
    user="root",
    passwd="1234",
    db="home_monitoring"
)

db.autocommit(True)  # 자동 커밋 활성화
cursor = db.cursor()

# "dht22_data" 테이블 생성
cursor.execute("""
    CREATE TABLE IF NOT EXISTS dht22_data (
        id INT AUTO_INCREMENT PRIMARY KEY,
        temperature FLOAT,
        humidity FLOAT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

# 최대 저장 개수
MAX_DATA_COUNT = 10

# DHT22 센서에서 온습도 값을 읽어오는 함수
def read_temperature_humidity():
    sensor = Adafruit_DHT.DHT22
    pin = 18  # DHT22 센서에 연결된 GPIO 핀 번호
    humidity, temperature = Adafruit_DHT.read_retry(sensor, pin)
    return temperature, humidity

# 온습도 값을 MySQL 데이터베이스에 저장하는 함수
def save_temperature_humidity(temperature, humidity):
    # 새로운 데이터 저장
    query = "INSERT INTO dht22_data (temperature, humidity) VALUES (%s, %s)"
    values = (temperature, humidity)
    cursor.execute(query, values)
    db.commit()

    # 데이터 개수 확인 및 제한
    query = f"SELECT COUNT(*) FROM dht22_data"
    cursor.execute(query)
    count = cursor.fetchone()[0]
    if count > MAX_DATA_COUNT:
        # 오래된 데이터 삭제
        query = f"DELETE FROM dht22_data ORDER BY id ASC LIMIT {count - MAX_DATA_COUNT}"
        cursor.execute(query)
        db.commit()

# 온도와 습도 값을 가져와서 JSON 형식으로 반환하는 함수
def get_temperature_humidity():
    query = "SELECT temperature, humidity FROM dht22_data ORDER BY id DESC LIMIT 10"
    cursor.execute(query)
    data = cursor.fetchall()
    temperature = [row[0] for row in data[::-1]]  # 최신 10개 온도 값을 역순으로 저장
    humidity = [row[1] for row in data[::-1]]  # 최신 10개 습도 값을 역순으로 저장
    return temperature, humidity

# 최신 온도와 습도 값을 가져오는 함수
# def get_latest_temperature_humidity():
#     query = "SELECT temperature, humidity FROM dht22_data ORDER BY id DESC LIMIT 1"
#     cursor.execute(query)
#     data = cursor.fetchone()
#     if data:
#         temperature = round(data[0], 1)
#         humidity = round(data[1], 1)
#     else:
#         temperature = None
#         humidity = None
#     return temperature, humidity

# 루트 URL('/')에 대한 핸들러 함수
@app.route('/')
def index():
    temperature_history, humidity_history = get_temperature_humidity()
    return render_template('index.html', temperature_history=temperature_history, humidity_history=humidity_history)

# 온도와 습도 값을 JSON 형식으로 반환하는 API 엔드포인트
@app.route('/api/data')
def data():
    temperature_history, humidity_history = get_temperature_humidity()
    return jsonify(temperature=temperature_history, humidity=humidity_history)

# DHT22 센서에서 데이터를 5초마다 읽어와서 MySQL 데이터베이스에 저장하는 함수
def read_and_save_temperature_humidity():
    while True:
        temperature, humidity = read_temperature_humidity()
        temperature = round(temperature, 1)  # 온도를 소숫점 한 자리까지 반올림
        humidity = round(humidity, 1)  # 습도를 소숫점 한 자리까지 반올림
        save_temperature_humidity(temperature, humidity)
        time.sleep(10)  # 5초 대기

# 애플리케이션 실행 시 DHT22 데이터 수집 및 저장을 위한 스레드 시작
if __name__ == '__main__':
    # DHT22 데이터 수집 및 저장 스레드 시작
    dht_thread = threading.Thread(target=read_and_save_temperature_humidity)
    dht_thread.daemon = True
    dht_thread.start()

    # Flask 애플리케이션 실행
    app.run(debug=True)

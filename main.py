from flask import Flask, render_template, Response, jsonify
from picamera2 import Picamera2
import cv2
import serial
import time
import subprocess
import threading

app = Flask(__name__)

# Global flags
rotate_video = False

# Setup serial connection to Arduino
SERIAL_PORT = '/dev/ttyUSB0'
BAUD_RATE = 9600
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)
except serial.SerialException:
    ser = None
    print("Warning: Could not connect to Arduino")

# Start camera in background
picam2 = Picamera2()
def start_camera():
    picam2.configure(picam2.create_video_configuration(
        main={"size": (640, 480)},  # lower resolution to reduce CPU
        controls={"FrameDurationLimits": (66666, 66666)}  # ~15 FPS
    ))
    picam2.start()

camera_thread = threading.Thread(target=start_camera)
camera_thread.start()

def generate_frames():
    global rotate_video
    while True:
        try:
            frame = picam2.capture_array()
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            if rotate_video:
                frame = cv2.rotate(frame, cv2.ROTATE_180)
            _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])  # reduce JPEG quality
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        except Exception as e:
            print(f"Frame error: {e}")
            time.sleep(1)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/move/<direction>', methods=['POST'])
def move(direction):
    command_map = {
        'forward': 'FORWARD 150',
        'backward': 'BACKWARD 150',
        'left': 'LEFT 150',
        'right': 'RIGHT 150',
        'stop': 'STOP'
    }
    if ser and direction in command_map:
        ser.write((command_map[direction] + '\n').encode())
    return '', 204

@app.route('/flip', methods=['POST'])
def flip():
    global rotate_video
    rotate_video = not rotate_video
    return '', 204

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/system_stats')
def system_stats():
    # CPU usage
    try:
        with open('/proc/stat', 'r') as f:
            line1 = f.readline()
            parts1 = line1.split()
            total1 = sum(map(int, parts1[1:]))
            idle1 = int(parts1[4])

        time.sleep(0.1)

        with open('/proc/stat', 'r') as f:
            line2 = f.readline()
            parts2 = line2.split()
            total2 = sum(map(int, parts2[1:]))
            idle2 = int(parts2[4])

        total_delta = total2 - total1
        idle_delta = idle2 - idle1
        cpu_usage = 100 * (total_delta - idle_delta) / total_delta
        cpu_usage = f"{cpu_usage:.1f}"
    except Exception as e:
        print(f"CPU error: {e}")
        cpu_usage = "Unavailable"

    # Temperature
    try:
        temp_output = subprocess.check_output(['vcgencmd', 'measure_temp']).decode()
        temp_value = temp_output.split('=')[1].split("'")[0]
    except Exception as e:
        print(f"Temp error: {e}")
        temp_value = "Unavailable"

    return jsonify(cpu=f"{cpu_usage}%", temp=f"{temp_value}°C")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)


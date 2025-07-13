import os
import subprocess
from flask import Flask, Response, render_template
import serial
import time
import atexit

app = Flask(__name__)

# Global flip flag
rotate_video = False
process = None


# Setup serial connection to Arduino
SERIAL_PORT = '/dev/ttyUSB0'  # Adjust if needed
BAUD_RATE = 9600
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)  # wait for Arduino reset
except serial.SerialException:
    ser = None
    print("Warning: Could not connect to Arduino")

# Close the serial port on exit when the app is shut down
@atexit.register
def cleanup():
    if ser:
        ser.close()

# Start libcamera-vid as background process
def start_camera():
    global process
    args = ['libcamera-vid', '-t', '0', '--codec', 'mjpeg', '--width', '640', '--height', '480']
    if rotate_video:
        args += ['--rotation', '180']
    args += ['-o', '-']
    # process = subprocess.Popen(args, stdout=subprocess.PIPE, bufsize=10**8)
    process = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,  # <-- suppresses stderr
        bufsize=10**8)

# Start camera at launch
start_camera()

def camera_stream():
    global process
    buffer = b''
    while True:
        chunk = process.stdout.read(1024)
        if not chunk:
            break
        buffer += chunk

        while b'\xff\xd8' in buffer and b'\xff\xd9' in buffer:
            start = buffer.find(b'\xff\xd8')
            end = buffer.find(b'\xff\xd9') + 2
            jpg = buffer[start:end]
            buffer = buffer[end:]
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + jpg + b'\r\n')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(camera_stream(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/move/<direction>')
def move(direction):
    command_map = {
        'forward': 'FORWARD 150',
        'backward': 'BACKWARD 150',
        'left': 'LEFT 150',
        'right': 'RIGHT 150',
        'stop': 'STOP'
    }
    try:
        if ser and direction in command_map:
            # Send the command to hardware (Arduino, motors, etc.)
            ser.write((command_map[direction] + '\n').encode())
        return ('', 200)
    except Exception as e:
        print(f"Error in /move/{direction}: {e}")
        return ('', 500)

@app.route('/flip')
def flip():
    global rotate_video, process
    rotate_video = not rotate_video
    try:
        process.terminate()
        process.wait()
        start_camera()
        print(f"Video flipped: rotation {'180' if rotate_video else '0'}")
        return ('', 200)
    except Exception as e:
        print(f"Error flipping video: {e}")
        return ('', 500)

@app.route('/restart/<service>')
def restart_service(service):
    if service not in ["flaskrobot", "nginx"]:
        return ('Invalid service', 400)
    subprocess.run(["sudo", "systemctl", "restart", f"{service}.service"])
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)

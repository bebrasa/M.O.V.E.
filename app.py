from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
import asyncio
from bleak import BleakClient
import numpy as np
import time
import threading
from scipy.signal import butter, lfilter, iirnotch

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///emg.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
socketio = SocketIO(app, async_mode='threading')

# BLE config
ESP32_MAC = "F0:F5:BD:FD:92:6E"
CHARACTERISTIC_UUID = "abcdef01-1234-5678-1234-56789abcdef0"

FS = 200

# Models
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    muscles = db.relationship('Muscle', backref='student', lazy=True)

class Muscle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    calib_min = db.Column(db.Float, nullable=True)
    calib_max = db.Column(db.Float, nullable=True)

with app.app_context():
    db.create_all()

# Globals for selected entities and calibration
selected_student_id = None
selected_muscle_id = None

LAMP_THRESHOLD = 43

value_buffer = []
fft_buffer = []
buffer_lock = threading.Lock()
fft_lock = threading.Lock()

lamp_status = False
history = []

collecting_calib_min_power = False
collecting_calib_max_power = False

calib_min_power_values = []
calib_max_power_values = []
calib_min_lock = threading.Lock()
calib_max_lock = threading.Lock()

calib_min = None
calib_max = None

def process_value(value):
    global lamp_status, history
    now = time.time()
    history.append((now, value))
    history = [(t, v) for t, v in history if now - t <= 1]
    lamp_status = len([v for t, v in history if abs(v) > LAMP_THRESHOLD]) >= 4

def butter_bandpass(lowcut, highcut, fs, order=4):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    return butter(order, [low, high], btype='band')

def apply_bandpass_filter(data):
    b, a = butter_bandpass(5, 99, FS, order=4)
    return lfilter(b, a, data)

def apply_notch_filter(data):
    b, a = iirnotch(50, 30, FS)
    return lfilter(b, a, data)

def handle_notification(sender, data):
    global collecting_calib_min_power, collecting_calib_max_power
    try:
        value = int(data.decode('utf-8').strip())
        process_value(value)
        with buffer_lock:
            value_buffer.append((time.time(), value))
        with fft_lock:
            fft_buffer.append(value)
            if len(fft_buffer) > 500:
                fft_buffer.pop(0)
    except Exception as e:
        print(f"[BLE] Error: {e}")

def emit_loop(start_time):
    try:
        while True:
            time.sleep(0.01)
            with buffer_lock:
                if not value_buffer:
                    continue
                ts, val = value_buffer[-1]
                value_buffer.clear()
            socketio.emit('update_plot', {
                'x': [ts - start_time],
                'y': [val],
                'lamp_status': lamp_status
            })
    except Exception as e:
        print(f"[emit_loop error] {e}")

def fft_loop():
    global collecting_calib_min_power, collecting_calib_max_power, calib_min, calib_max
    window_size = 256
    while True:
        time.sleep(0.1)
        with fft_lock:
            if len(fft_buffer) < window_size:
                continue
            data = np.array(fft_buffer[-window_size:])

        filtered = apply_bandpass_filter(data)
        filtered = apply_notch_filter(filtered)

        fft_res = np.fft.fft(filtered)
        magnitudes = np.abs(fft_res[:window_size//2])
        freqs = np.fft.fftfreq(window_size, d=1/FS)[:window_size//2]

        power = magnitudes ** 2
        total_power = np.sum(power)

        if collecting_calib_min_power:
            with calib_min_lock:
                calib_min_power_values.append(total_power)
        if collecting_calib_max_power:
            with calib_max_lock:
                calib_max_power_values.append(total_power)

        min_power_local = calib_min
        max_power_local = calib_max

        if min_power_local is None or max_power_local is None:
            min_power_local = 1909095491.6462147
            max_power_local = 25419549659.2756

        normalized_power = (total_power - min_power_local) / (max_power_local*1.3 - min_power_local)
        normalized_power = np.clip(normalized_power, 0, 1)
        percent_power = int(normalized_power * 100)

        socketio.emit('update_fft', {
            'freq': freqs.tolist(),
            'amp': magnitudes.tolist(),
            'percent_power': percent_power
        })

@socketio.on('start_stream')
def start_stream():
    threading.Thread(target=background_ble_loop, daemon=True).start()

@socketio.on('start_calibration_min')
def start_calibration_min():
    global collecting_calib_min_power, calib_min_power_values
    with calib_min_lock:
        collecting_calib_min_power = True
        calib_min_power_values = []
    socketio.emit('calibration_started_min')
    threading.Timer(5.0, finish_calibration_min).start()

@socketio.on('start_calibration_max')
def start_calibration_max():
    global collecting_calib_max_power, calib_max_power_values
    with calib_max_lock:
        collecting_calib_max_power = True
        calib_max_power_values = []
    socketio.emit('calibration_started_max')
    threading.Timer(5.0, finish_calibration_max).start()

def finish_calibration_min():
    global collecting_calib_min_power, calib_min, selected_muscle_id
    with calib_min_lock:
        collecting_calib_min_power = False
        if calib_min_power_values:
            twenty_min = sorted(calib_min_power_values)[:20]
            calib_min = float(np.mean(twenty_min))
        else:
            calib_min = None
    print(f"[CALIB] Минимум мощности: {calib_min}")

    with app.app_context():
        if selected_muscle_id and calib_min is not None:
            muscle = Muscle.query.get(selected_muscle_id)
            if muscle:
                muscle.calib_min = calib_min
                db.session.commit()

    socketio.emit('calibration_min_done', {'calib_min': calib_min})

def finish_calibration_max():
    global collecting_calib_max_power, calib_max, selected_muscle_id
    with calib_max_lock:
        collecting_calib_max_power = False
        if calib_max_power_values:
            twenty_max = sorted(calib_max_power_values, reverse=True)[:20]
            calib_max = float(np.mean(twenty_max))
        else:
            calib_max = None
    print(f"[CALIB] Максимум мощности: {calib_max}")

    with app.app_context():
        if selected_muscle_id and calib_max is not None:
            muscle = Muscle.query.get(selected_muscle_id)
            if muscle:
                muscle.calib_max = calib_max
                db.session.commit()

    socketio.emit('calibration_max_done', {'calib_max': calib_max})

def background_ble_loop():
    asyncio.run(run_ble_client())

async def run_ble_client():
    start_time = time.time()
    async with BleakClient(ESP32_MAC) as client:
        print(f"[BLE] Connected to {ESP32_MAC}")
        await client.start_notify(CHARACTERISTIC_UUID, handle_notification)
        threading.Thread(target=emit_loop, args=(start_time,), daemon=True).start()
        threading.Thread(target=fft_loop, daemon=True).start()
        while True:
            await asyncio.sleep(1)

# API endpoints for students and muscles

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/students', methods=['GET', 'POST'])
def api_students():
    if request.method == 'POST':
        data = request.json
        name = data.get('name')
        if not name:
            return jsonify({'error': 'Name required'}), 400
        s = Student(name=name)
        db.session.add(s)
        db.session.commit()
        return jsonify({'id': s.id, 'name': s.name})
    else:
        students = Student.query.all()
        return jsonify([{'id': s.id, 'name': s.name} for s in students])

@app.route('/api/students/<int:student_id>/muscles', methods=['GET', 'POST'])
def api_muscles(student_id):
    student = Student.query.get_or_404(student_id)
    if request.method == 'POST':
        data = request.json
        name = data.get('name')
        if not name:
            return jsonify({'error': 'Name required'}), 400
        m = Muscle(name=name, student=student)
        db.session.add(m)
        db.session.commit()
        return jsonify({'id': m.id, 'name': m.name, 'calib_min': m.calib_min, 'calib_max': m.calib_max})
    else:
        muscles = Muscle.query.filter_by(student_id=student_id).all()
        return jsonify([{'id': m.id, 'name': m.name, 'calib_min': m.calib_min, 'calib_max': m.calib_max} for m in muscles])

@app.route('/api/muscles/<int:muscle_id>/select', methods=['POST'])
def api_select_muscle(muscle_id):
    global selected_muscle_id, calib_min, calib_max
    muscle = Muscle.query.get_or_404(muscle_id)
    selected_muscle_id = muscle_id
    calib_min = muscle.calib_min
    calib_max = muscle.calib_max
    return jsonify({'success': True, 'calib_min': calib_min, 'calib_max': calib_max})

@app.route('/api/select_student', methods=['POST'])
def api_select_student():
    global selected_student_id, selected_muscle_id, calib_min, calib_max
    data = request.json
    sid = data.get('student_id')
    student = Student.query.get_or_404(sid)
    selected_student_id = sid
    selected_muscle_id = None
    calib_min = None
    calib_max = None
    return jsonify({'success': True})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5002)

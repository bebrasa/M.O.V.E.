from flask import Flask, render_template
from flask_socketio import SocketIO
import asyncio
from bleak import BleakClient
import numpy as np
import time
import threading
from scipy.signal import butter, lfilter

app = Flask(__name__, static_folder='static')
socketio = SocketIO(app, async_mode='threading')

ESP32_MAC = "F0:F5:BD:FD:92:6E"
CHARACTERISTIC_UUID = "abcdef01-1234-5678-1234-56789abcdef0"

value_buffer = []
fft_buffer = []
buffer_lock = threading.Lock()
fft_lock = threading.Lock()

lamp_status = False
history = []

@app.route('/')
def index():
    return render_template('index.html')

def process_value(value):
    global lamp_status, history
    current_time = time.time()
    history.append((current_time, value))
    history = [(t, v) for t, v in history if current_time - t <= 1]
    lamp_status = len([v for t, v in history if abs(v) > 43]) >= 4

def handle_notification(sender, data):
    try:
        line = data.decode('utf-8').strip()
        value = int(line)
        value = max(-300, min(300, value))
        process_value(value)

        with buffer_lock:
            value_buffer.append((time.time(), value))
        with fft_lock:
            fft_buffer.append(value)
            if len(fft_buffer) > 256:
                fft_buffer.pop(0)

    except Exception as e:
        print(f"[BLE] Ошибка: {e}")

def emit_loop(start_time):
    last_emit = 0
    while True:
        time.sleep(0.05)

        with buffer_lock:
            if not value_buffer:
                continue
            timestamp, value = value_buffer[-1]
            value_buffer.clear()

        if time.time() - last_emit >= 0.05:
            last_emit = time.time()
            socketio.emit('update_plot', {
                'x': [timestamp - start_time],
                'y': [value],
                'lamp_status': lamp_status
            })

# Полосовой фильтр Баттерворта
def butter_bandpass(lowcut, highcut, fs, order=4):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    return butter(order, [low, high], btype='band')

def apply_bandpass_filter(data, lowcut=1, highcut=100, fs=1000):
    b, a = butter_bandpass(lowcut, highcut, fs, order=4)
    return lfilter(b, a, data)

def fft_loop():
    while True:
        time.sleep(0.5)
        with fft_lock:
            if len(fft_buffer) < 64:
                continue
            data = np.array(fft_buffer[-256:])
            # Применяем фильтрацию
            data = apply_bandpass_filter(data, lowcut=5, highcut=100, fs=1000)
            
            fft_result = np.fft.fft(data)
            freqs = np.fft.fftfreq(len(data), d=1/100)  # Частота дискретизации ~100 Гц
            magnitudes = np.abs(fft_result[:len(data)//2])
            freqs = freqs[:len(data)//2]

            # Расширяем ось частоты до 120 Гц
            extended_freqs = np.linspace(0, 120, len(magnitudes))
        
        socketio.emit('update_fft', {
            'freq': extended_freqs.tolist(),
            'amp': magnitudes.tolist()
        })


@socketio.on('start_stream')
def start_stream():
    threading.Thread(target=background_ble_loop, daemon=True).start()

def background_ble_loop():
    asyncio.run(run_ble_client())

async def run_ble_client():
    start_time = time.time()
    async with BleakClient(ESP32_MAC) as client:
        print("[BLE] Подключено")
        await client.start_notify(CHARACTERISTIC_UUID, handle_notification)
        threading.Thread(target=emit_loop, args=(start_time,), daemon=True).start()
        threading.Thread(target=fft_loop, daemon=True).start()
        while True:
            await asyncio.sleep(1)

if __name__ == '__main__':

    socketio.run(app, host='0.0.0.0', port=5001, debug=True)

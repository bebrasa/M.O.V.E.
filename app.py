from flask import Flask, render_template
from flask_socketio import SocketIO
import asyncio
from bleak import BleakClient
import numpy as np
import time
import threading
from scipy.signal import butter, lfilter, iirnotch

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

packet_count = 0
last_print_time = 0

def handle_notification(sender, data):
    global packet_count, last_print_time
    try:
        line = data.decode('utf-8').strip()
        value = int(line)
        value = max(-300, min(300, value))
        process_value(value)

        with buffer_lock:
            value_buffer.append((time.time(), value))
        with fft_lock:
            fft_buffer.append(value)
            if len(fft_buffer) > 300:
                fft_buffer.pop(0)

        packet_count += 1
        now = time.time()
        if now - last_print_time >= 1.0:
            print(f"[BLE] Скорость: {packet_count} пакетов/сек")
            packet_count = 0
            last_print_time = now

    except Exception as e:
        print(f"[BLE] Ошибка: {e}")

def emit_loop(start_time):
    last_emit = 0
    while True:
        time.sleep(0.005)

        with buffer_lock:
            if not value_buffer:
                continue
            timestamp, value = value_buffer[-1]
            value_buffer.clear()

        # if time.time() - last_emit >= 0.05:
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


def apply_notch_filter(data, freq, fs, Q=30):
    """
    freq — частота, которую надо подавить (например, 27 Гц)
    fs — частота дискретизации
    Q — добротность (чем выше, тем уже фильтр)
    """
    b, a = iirnotch(freq, Q, fs)
    filtered = lfilter(b, a, data)
    return filtered


def fft_loop():
    window_size = 200       # длина окна FFT
    stride = 50             # шаг окна
    fs = 200               # частота дискретизации

    while True:
        time.sleep(0.1)

        with fft_lock:
            if len(fft_buffer) < window_size + stride:
                continue

            # Копируем данные (без очистки буфера)
            data = np.array(fft_buffer[-(window_size + stride * 3):])  # берём немного больше для 3 окон

        spectra = []
        freqs = None

        for start in range(0, len(data) - window_size + 1, stride):
            segment = data[start:start + window_size]

            # Фильтрация
            segment = apply_bandpass_filter(segment, lowcut=5, highcut=99, fs=fs)

            # FFT
            fft_result = np.fft.fft(segment)
            magnitudes = np.abs(fft_result[:window_size // 2])
            freqs = np.fft.fftfreq(window_size, d=1 / fs)[:window_size // 2]

            spectra.append(magnitudes)

        # Среднее по окнам
        avg_spectrum = np.mean(spectra, axis=0)

        # Удалим слишком низкие частоты (например, <5 Гц)
        mask = freqs > 5
        filtered_freqs = freqs[mask]
        filtered_magnitudes = avg_spectrum[mask]

        # Нормализуем мощность
        power = filtered_magnitudes ** 2
        total_power = np.sum(power)
        

        min_power = 2301935*2
        max_power = 314517627*2

        normalized_power = (total_power - min_power) / (max_power - min_power)
        normalized_power = np.clip(normalized_power, 0, 1)
        percent_power = int(normalized_power * 100)

        # Отправляем спектр и мощность
        socketio.emit('update_fft', {
            'freq': filtered_freqs.tolist(),
            'amp': filtered_magnitudes.tolist(),
            'percent_power': percent_power
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

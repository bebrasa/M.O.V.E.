# emg_processor.py
import asyncio
from bleak import BleakClient
import numpy as np
import time
import threading
from scipy.signal import butter, lfilter, iirnotch

ESP32_MAC = "F0:F5:BD:FD:92:6E"
CHARACTERISTIC_UUID = "abcdef01-1234-5678-1234-56789abcdef0"

LAMP_THRESHOLD = 43
BANDPASS_MIN = 5
BANDPASS_MAX = 99
NOTCH_FREQ = 50
NOTCH_Q = 30

value_buffer = []
fft_buffer = []
buffer_lock = threading.Lock()
fft_lock = threading.Lock()
lamp_status = False
history = []

calib_min = None
calib_max = None
collecting_calibration = False
calib_samples = []
calib_lock = threading.Lock()

socketio = None  # Установим его позже из app.py

def init_socketio(sio):
    global socketio
    socketio = sio

def process_value(value):
    global lamp_status, history
    now = time.time()
    history.append((now, value))
    history = [(t, v) for t, v in history if now - t <= 1]
    lamp_status = len([v for t, v in history if abs(v) > LAMP_THRESHOLD]) >= 4

    with calib_lock:
        if collecting_calibration:
            calib_samples.append(value)

def butter_bandpass(lowcut, highcut, fs, order=4):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    return butter(order, [low, high], btype='band')

def apply_bandpass_filter(data):
    b, a = butter_bandpass(BANDPASS_MIN, BANDPASS_MAX, fs=200)
    return lfilter(b, a, data)

def apply_notch_filter(data):
    b, a = iirnotch(NOTCH_FREQ, NOTCH_Q, fs=200)
    return lfilter(b, a, data)

def handle_notification(sender, data):
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

def fft_loop():
    window_size = 256
    fs = 200
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
        freqs = np.fft.fftfreq(window_size, d=1/fs)[:window_size//2]
        power = magnitudes ** 2
        total_power = np.sum(power)

        min_power = 1909095491.6462147
        max_power = 25419549659.2756

        normalized_power = (total_power - min_power) / (max_power - min_power)
        normalized_power = np.clip(normalized_power, 0, 1)
        percent_power = int(normalized_power * 100)

        socketio.emit('update_fft', {
            'freq': freqs.tolist(),
            'amp': magnitudes.tolist(),
            'percent_power': percent_power
        })

async def run_ble_client():
    start_time = time.time()
    async with BleakClient(ESP32_MAC) as client:
        print(f"[BLE] Connected to {ESP32_MAC}")
        await client.start_notify(CHARACTERISTIC_UUID, handle_notification)
        threading.Thread(target=emit_loop, args=(start_time,), daemon=True).start()
        threading.Thread(target=fft_loop, daemon=True).start()
        while True:
            await asyncio.sleep(1)

def background_ble_loop():
    asyncio.run(run_ble_client())

def start_dynamic_calibration(duration=5.0):
    global collecting_calibration, calib_samples
    with calib_lock:
        collecting_calibration = True
        calib_samples = []
    threading.Timer(duration, finish_dynamic_calibration).start()

def finish_dynamic_calibration():
    global collecting_calibration, calib_min, calib_max
    with calib_lock:
        if calib_samples:
            calib_min = min(calib_samples)
            calib_max = max(calib_samples)
        collecting_calibration = False
    print(f"[CALIB] Done: min={calib_min}, max={calib_max}")
    socketio.emit('dynamic_calibration_done', {
        'calib_min': calib_min,
        'calib_max': calib_max
    })

def reset_dynamic_calibration():
    global calib_min, calib_max, collecting_calibration, calib_samples
    with calib_lock:
        calib_min = None
        calib_max = None
        collecting_calibration = False
        calib_samples = []
    print("[CALIB] Reset to default")
    socketio.emit('dynamic_calibration_reset')
from flask import Flask, render_template
from flask_socketio import SocketIO
import serial
import eventlet
import time

# Настройка Flask
app = Flask(__name__)
socketio = SocketIO(app, async_mode='eventlet')

# Настройка последовательного порта
port = '/dev/tty0'  # Замените на реальный порт
baud_rate = 115200
ser = serial.Serial(port, baud_rate, timeout=1)

# Данные для графика
x_data = []
y_data = []
active_start_time = None  # Время, когда мышца стала активной
lamp_status = False       # Состояние "лампочки"

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('start_stream')
def stream_data():
    global x_data, y_data, active_start_time, lamp_status

    start_time = time.time()

    while True:
        if ser.in_waiting > 0:
            try:
                line_data = ser.readline().decode('utf-8').strip()
                value = int(line_data)
                value = max(0, min(255, value))  # Ограничение диапазона значений
                print(f"Получены данные: {value}")
            except ValueError:
                print(f"Ошибка преобразования: '{line_data}'")
                continue

            current_time = time.time() - start_time
            if value < 100:
                value = 0

            y_data.append(value)
            x_data.append(current_time)

            # Ограничение данных на графике
            if len(y_data) > 100:
                y_data.pop(0)
                x_data.pop(0)

            # Проверка активации мышцы
            if value > 100:  # Условие активации мышцы
                if active_start_time is None:
                    active_start_time = time.time()  # Запоминаем начало активации
                elif time.time() - active_start_time >= 2:  # Если прошло 2 секунды
                    lamp_status = True
            else:
                active_start_time = None  # Сбрасываем время, если мышца не активна
                lamp_status = False

            # Отправка данных клиенту
            socketio.emit('update_plot', {'x': x_data, 'y': y_data, 'lamp_status': lamp_status})
        eventlet.sleep(0.01)

if __name__ == '__main__':
    socketio.run(app, host='127.0.0.1', port=5001, debug=True)


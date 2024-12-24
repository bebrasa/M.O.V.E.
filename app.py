from flask import Flask, render_template
from flask_socketio import SocketIO
import serial
import eventlet
import time

# Настройка Flask
app = Flask(__name__)
socketio = SocketIO(app, async_mode='eventlet')

# Настройка последовательного порта
port = '/dev/cu.usbmodem1101'  # Замените на реальный порт
baud_rate = 115200
ser = serial.Serial(port, baud_rate, timeout=1)

# Функция для сглаживания данных
def smooth_data(data, window_size=5):
    if len(data) < window_size:
        return data[-1]  # Если данных меньше окна сглаживания, вернуть последний элемент
    return sum(data[-window_size:]) / window_size  # Скользящее среднее

# Данные для графика
x_data = []
y_data = []
history = []  # Храним список значений сигнала с временными метками
lamp_status = False  # Состояние "лампочки"

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('start_stream')
def stream_data():
    global x_data, y_data, history, lamp_status

    start_time = time.time()

    while True:
        if ser.in_waiting > 0:
            try:
                # Чтение значения из последовательного порта
                line_data = ser.readline().decode('utf-8').strip()
                value = int(line_data)
                value = max(-300, min(300, value))  # Ограничение диапазона

                # Добавляем значение в историю
                current_time = time.time()
                history.append((current_time, value))

                # Удаляем значения старше 2 секунд
                history = [(t, v) for t, v in history if current_time - t <= 1]

                # Подсчет значений, превышающих порог
                exceeding_values = [v for t, v in history if v > 43 or v < -43]

                # Логика активации лампочки
                if len(exceeding_values) >= 4 :
                    lamp_status = True
                else:
                    lamp_status = False

                # Логирование для отладки
                print(f"История: {history}")
                print(f"Значения превышающие порог: {exceeding_values}, Лампочка: {lamp_status}")

                # Добавление данных для графика
                y_data.append(value)
                x_data.append(current_time - start_time)

                # Ограничение количества точек на графике
                if len(y_data) > 100:
                    y_data.pop(0)
                    x_data.pop(0)

                # Отправка данных клиенту
                socketio.emit('update_plot', {'x': x_data, 'y': y_data, 'lamp_status': lamp_status})

            except ValueError:
                print(f"Ошибка преобразования: '{line_data}'")
                continue

        eventlet.sleep(0)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5001, debug=True)

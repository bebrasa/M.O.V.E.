from flask import Flask, render_template
from flask_socketio import SocketIO
import graphic
import eventlet

# Создание приложения Flask
app = Flask(__name__)
socketio = SocketIO(app, async_mode='eventlet')

# Переменные для данных
x_data = []
y_data = []

@app.route('/')
def index():
    return render_template('index.html')

# Обработка подключения
@socketio.on('start_stream')
def stream_data():
    global x_data, y_data

    import time
    start_time = time.time()

    while True:
        # Получение данных с Arduino
        value = graphic.get_data()
        current_time = time.time() - start_time

        # Обновление данных
        y_data.append(value)
        x_data.append(current_time)

        # Ограничение длины данных
        if len(y_data) > 100:
            y_data.pop(0)
            x_data.pop(0)

        # Отправка данных клиенту
        print(f"Отправка точек данных: {len(y_data)}")
        socketio.emit('update_plot', {'x': x_data, 'y': y_data})

        eventlet.sleep(0.05)

if __name__ == '__main__':
    socketio.run(app, debug=True)
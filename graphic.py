import random
import serial

# Переключатель между эмуляцией и реальностью
USE_ARDUINO = False  

# Глобальная переменная
filtrdVal = 0

if USE_ARDUINO:
    port = '/dev/ttyACM0'  # Обновите на реальный порт
    baud_rate = 115200
    ser = serial.Serial(port, baud_rate, timeout=1)

# Получение данных
def get_data():
    global filtrdVal  # Указываем, что изменяем глобальную переменную

    if USE_ARDUINO:
        if ser.in_waiting > 0:
            try:
                line_data = ser.readline().decode('utf-8').strip()
                value = int(line_data)
                filtrdVal = value
                print(f"Получены данные с Arduino: {filtrdVal}")
                return filtrdVal
            except ValueError:
                print("Ошибка чтения данных")
                return 0
    else:
        # Эмуляция данных
        value = random.randint(-255, 255)
        print(f"Сгенерированные данные: {value}")
        return value
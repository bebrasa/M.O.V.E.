import serial

# Настройка порта Arduino
port = '/dev/cu.usbmodem1401'  # Замените на реальный порт
baud_rate = 115200

# Инициализация последовательного порта
ser = serial.Serial(port, baud_rate, timeout=1)

# Получение данных
def get_data():
    if ser.in_waiting > 0:
        try:
            line_data = ser.readline().decode('utf-8').strip()
            value = int(line_data)
            filtered_value = int(0)
            if value>60 : 
                filtered_value=value
            print(f"Получены данные: {filtered_value}")  # Отладка
            return filtered_value
        except ValueError:
            print("Ошибка чтения данных")
            return 0
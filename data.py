from pybv import write_brainvision
import serial
import time
import numpy as np

# Настройки Arduino
arduino_port = "/dev/ttyACM0"  # Замените на ваш порт
baud_rate = 115200
sampling_frequency = 1000  # Частота выборки (Гц)
record_duration = 10000       # Длительность записи (в секундах)

# Подключение к Arduino
arduino = serial.Serial(arduino_port, baud_rate)
time.sleep(2)  # Ожидание подключения

# Настройки данных
n_samples = sampling_frequency * record_duration
data = np.zeros(n_samples)  # Массив для записи данных

# Сбор данных
print("Сбор данных...")
start_time = time.time()
for i in range(n_samples):
    if arduino.in_waiting > 0:
        try:
            # Считываем данные из Arduino
            raw_value = int(arduino.readline().decode('utf-8').strip())
            data[i] = raw_value
        except ValueError:
            pass

arduino.close()  # Закрываем соединение
print("Сбор данных завершен!")

# Преобразование данных в микровольты
data = (data / 1023.0) * 5000  # Пример преобразования (зависит от датчика)

# Запись в формате BrainVision
print("Запись в формате BrainVision...")
ch_names = ["EMG"]  # Названия каналов
write_brainvision(
    data=data.reshape(1, -1),  # Преобразуем в двумерный массив
    sfreq=sampling_frequency,  # Частота выборки
    ch_names=ch_names,         # Названия каналов
    fname_base="emg_data",      # Базовое имя файла
    folder_out="./CLionProjects/"  # Папка для сохранения файлов
)
print("Запись завершена! Файлы сохранены в ./CLionProjects/")

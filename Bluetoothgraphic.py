import asyncio
import matplotlib.pyplot as plt
import numpy as np
from bleak import BleakClient

# 🔹 Укажите MAC-адрес ESP32-C3
ESP32_MAC = "F0:F5:BD:FD:92:6E"

# 🔹 UUID характеристики с данными
CHARACTERISTIC_UUID = "abcdef01-1234-5678-1234-56789abcdef0"

# 🔹 Хранилище данных для графика
x_data = []
y_data = []

# 🔹 Настройка графика
plt.ion()  # Включаем интерактивный режим
fig, ax = plt.subplots()
line, = ax.plot([], [], 'b-', label="Сигнал")
ax.set_xlim(0, 1000)
ax.set_ylim(-300, 300)
ax.set_xlabel("Время")
ax.set_ylabel("Значение")
ax.legend()

async def read_ble():
    async with BleakClient(ESP32_MAC) as client:
        print("✅ Подключено к ESP32-C3")

        def notification_handler(sender, data):
            global x_data, y_data

            try:
                value = int(data.decode('utf-8'))
                print(f"📡 Получено значение: {value}")

                # Добавляем новые данные
                x_data.append(len(x_data))
                y_data.append(value)


                # Обновление графика
                line.set_xdata(x_data)
                line.set_ydata(y_data)
                ax.set_xlim(min(x_data), max(x_data) + 10)
                ax.relim()
                ax.autoscale_view(True, True, True)
                plt.draw()
                plt.pause(0.01)

            except ValueError:
                print(f"❌ Ошибка преобразования: '{data}'")

        # Подписка на уведомления
        await client.start_notify(CHARACTERISTIC_UUID, notification_handler)

        print("📡 Ожидание данных...")
        while True:
            await asyncio.sleep(0.1)

# Запуск BLE-чтения
asyncio.run(read_ble())

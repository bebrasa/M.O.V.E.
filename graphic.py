import serial
import time
import matplotlib.pyplot as plt

port = '/dev/tty.usbmodem101'
baud_rate = 115200

ser = serial.Serial(port, baud_rate)
time.sleep(2)

plt.ion()
fig, ax = plt.subplots()
y_data = []
x_data = []
line, = ax.plot(x_data, y_data)

ax.set_ylim(-15, 30)

start_time = time.time()

try:
    while True:
        if ser.in_waiting > 0:
            line_data = ser.readline().decode('utf-8').strip()
            try:
                filtered_value = int(line_data)

                current_time = time.time() - start_time
                y_data.append(filtered_value)
                x_data.append(current_time)

                if len(y_data) > 100:
                    y_data.pop(0)
                    x_data.pop(0)

                line.set_xdata(x_data)
                line.set_ydata(y_data)
                ax.relim()
                ax.autoscale_view()
                plt.draw()
                plt.pause(0.01)

            except ValueError:
                print(f"Невозможно преобразовать: {line_data}")
except KeyboardInterrupt:
    print("Завершение работы программы.")
finally:
    ser.close()
    plt.ioff()
    plt.show()
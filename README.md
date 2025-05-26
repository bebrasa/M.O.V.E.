# EMG 
A platform connected to an EMG device (via BLE) for real-time muscle signal visualization and calibration.  
Allows managing a database of users and their muscles, storing calibration values.

---

## Features

- Connects to EMG sensor via BLE (ESP32)
- Real-time visualization of EMG signal (waveform and FFT spectrum)
- Calibration of minimum and maximum signal power levels
- Management of students and muscles database (create, select, store calibrations)
- Web interface with interactive charts and user-friendly UI

---

## Technologies

- Python 3.x
- Flask + Flask-SocketIO
- SQLAlchemy + SQLite
- Bleak (BLE client)
- NumPy, SciPy
- Plotly.js
- HTML/CSS/JavaScript

---

## Installation

1. Clone the repository or copy the project files.

## Install dependencies

pip install -r requirements.txt

## run 

python app.py

## Open your web browser and navigate to:

http://localhost:5002

import cv2
import mediapipe as mp
import time
#import serial  # Для работы с EMG через Arduino

# Подключаем камеру
cap = cv2.VideoCapture(0)

# Настраиваем MediaPipe
mp_drawing = mp.solutions.drawing_utils
mp_holistic = mp.solutions.holistic

# Время для расчета FPS
pTime = 0
cTime = 0

# Подключение к Arduino через Serial для данных EMG
#emg_serial = serial.Serial('/dev/ttyUSB0', 9600)  # Проверьте COM порт

# Функция для распознавания сжатого кулака
def is_fist(hand_landmarks):
    if hand_landmarks:
        fingers = []
        for lm in [8, 12, 16, 20]:  # Кончики пальцев
            if hand_landmarks.landmark[lm].y < hand_landmarks.landmark[lm-2].y:
                fingers.append(1)
            else:
                fingers.append(0)
        if all(finger == 0 for finger in fingers):
            return True
    return False

# Функция для чтения данных EMG
# def get_emg_data():
#     if emg_serial.in_waiting > 0:
#         try:
#             emg_value = emg_serial.readline().decode('utf-8').strip()
#             return int(emg_value)  # Читаем значение EMG с Arduino
#         except:
#             return 0
#     return 0

# Зацикливаем получение кадров от камеры
with mp_holistic.Holistic(min_detection_confidence=0.5, 
                          min_tracking_confidence=0.5, 
                          refine_face_landmarks=False) as holistic:  # Отключаем детекцию лица
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print("Не удалось получить кадр с камеры")
            break

        # Перекрашиваем изображение из BGR в RGB для обработки в MediaPipe
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Обработка изображения в MediaPipe
        results = holistic.process(image)
        
        # Перекрашиваем изображение обратно в BGR для отображения
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        # Отрисовка скелета
        mp_drawing.draw_landmarks(image, results.pose_landmarks, mp_holistic.POSE_CONNECTIONS,
                                  mp_drawing.DrawingSpec(color=(245,117,66), thickness=2, circle_radius=4),
                                  mp_drawing.DrawingSpec(color=(245,66,230), thickness=2, circle_radius=2))

        # # Получаем данные EMG
        # emg_value = get_emg_data()
        # cv2.putText(image, f'EMG: {emg_value}', (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)

        # Отрисовка рук с проверкой на кулак
        if results.right_hand_landmarks:
            mp_drawing.draw_landmarks(image, results.right_hand_landmarks, mp_holistic.HAND_CONNECTIONS,
                                      mp_drawing.DrawingSpec(color=(80,22,10), thickness=2, circle_radius=4),
                                      mp_drawing.DrawingSpec(color=(80,44,121), thickness=2, circle_radius=2))

            if is_fist(results.right_hand_landmarks):
                cv2.putText(image, 'Right Fist Detected', (500, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        if results.left_hand_landmarks:
            mp_drawing.draw_landmarks(image, results.left_hand_landmarks, mp_holistic.HAND_CONNECTIONS,
                                      mp_drawing.DrawingSpec(color=(121,22,76), thickness=2, circle_radius=4),
                                      mp_drawing.DrawingSpec(color=(121,44,250), thickness=2, circle_radius=2))

            if is_fist(results.left_hand_landmarks):
                cv2.putText(image, 'Left Fist Detected', (500, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        # Расчет и отображение FPS
        cTime = time.time()
        fps = 1 / (cTime - pTime)
        pTime = cTime
        
        cv2.putText(image, f'FPS: {int(fps)}', (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
        
        # Отображение изображения
        cv2.imshow('M.O.V.E. Tracking with EMG', image)
        
        # Прерывание по нажатию клавиши ESC
        if cv2.waitKey(1) & 0xFF == 27:
            break

# Освобождение ресурсов
cap.release()
cv2.destroyAllWindows()
emg_serial.close()
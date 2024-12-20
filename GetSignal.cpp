#include <TimerOne.h>  // Подключаем библиотеку TimerOne для использования функций Таймера1

int val = 0;

void sendData() {
  val = analogRead(A0);

  Serial.println(map(val, 0, 1023, -255, 255));
}

void setup() {
  Serial.begin(115200);                 // Инициализируем Serial-порт на скорости 115200 Кбит/с
  Timer1.initialize(10000);              // Инициализируем Таймер1 с интервалом 3000 микросекунд (3 мс)
  Timer1.attachInterrupt(sendData);     // Привязываем функцию sendData к прерыванию таймера
}

void loop() {
  // Пустой цикл, так как Таймер1 вызывает функцию sendData каждые 3000 микросекунд
}
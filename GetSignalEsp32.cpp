#define ANALOG_PIN A0  // Аналоговый пин ESP32 (обычно это GPIO36)

void setup() {
    Serial.begin(115200); // Запускаем последовательную связь
}

void loop() {
    int analogValue = analogRead(ANALOG_PIN); // Читаем аналоговое значение
    Serial.println(analogValue); // Выводим значение в монитор порта
    delay(1000); // Задержка 1 секунда
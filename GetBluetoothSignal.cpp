#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEServer.h>

#define SERVICE_UUID "12345678-1234-5678-1234-56789abcdef0"
#define CHARACTERISTIC_UUID "abcdef01-1234-5678-1234-56789abcdef0"
#define ANALOG_PIN 4  // GPIO4 для аналогового входа

BLEServer *pServer = NULL;
BLECharacteristic *pCharacteristic = NULL;

void setup() {
    Serial.begin(115200);
    BLEDevice::init("ESP32-C3-BLE");  // Имя устройства
    pServer = BLEDevice::createServer();

    // Создаём BLE-сервис
    BLEService *pService = pServer->createService(SERVICE_UUID);

    // Характеристика для передачи данных
    pCharacteristic = pService->createCharacteristic(
                        CHARACTERISTIC_UUID,
                        BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_NOTIFY
                      );

    pCharacteristic->setValue("0"); // Начальное значение
    pService->start();

    // Начинаем рекламу
    BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
    pAdvertising->addServiceUUID(SERVICE_UUID);
    pAdvertising->start();
}

void loop() {
    int val = analogRead(ANALOG_PIN); // Читаем аналоговый вход
    int mappedVal = map(val, 0, 4095, -255, 255); // Преобразуем диапазон
    String value = String(mappedVal);
    
    Serial.println(value);  // Вывод в Serial Monitor
    pCharacteristic->setValue(value.c_str()); // Обновляем BLE-значение
    pCharacteristic->notify(); // Уведомляем клиентов

    delay(100); // Ждем 100 мс перед следующим измерением
}

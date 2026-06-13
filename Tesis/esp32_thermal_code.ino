/*
 * Código para ESP32-S3 con Cámara Térmica IR
 * Módulo: Módulo de Cámara Termográfica IR Esp32-s3, Equipado Con Esp3
 
#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <ArduinoJson.h>

// Configuración WiFi
const char* ssid = "YOUR_SSID";
const char* password = "YOUR_PASSWORD";
const char* server = "http://localhost:5000";  // URL del servidor Python

// Variables globales
WiFiClient wifiClient;
HTTPClient http;
unsigned long lastSendTime = 0;
const unsigned long SEND_INTERVAL = 2000;  // Enviar cada 2 segundos

// Direcciones I2C
#define THERMAL_CAMERA_ADDR 0x68  // Dirección típica de AMG8833
#define SENSOR_COLS 8
#define SENSOR_ROWS 8

// Datos de temperatura
float thermalData[SENSOR_ROWS][SENSOR_COLS];
float ambientTemp = 25.0;

// Función para conectar a WiFi
void setupWiFi() {
    Serial.print("Conectando a WiFi: ");
    Serial.println(ssid);
    
    WiFi.begin(ssid, password);
    int attempts = 0;
    
    while (WiFi.status() != WL_CONNECTED && attempts < 20) {
        delay(500);
        Serial.print(".");
        attempts++;
    }
    
    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\n WiFi conectado");
        Serial.print("IP: ");
        Serial.println(WiFi.localIP());
    } else {
        Serial.println("\n No se pudo conectar a WiFi");
    }
}

// Función para inicializar la cámara térmica
void setupThermalCamera() {
    Wire.begin(21, 22);  // SDA=21, SCL=22 (ESP32-S3)
    delay(100);
    
    // Inicializar sensor
    if (Wire.begin(21, 22, 100000)) {
        Serial.println(" I2C inicializado correctamente");
    } else {
        Serial.println(" Error inicializando I2C");
    }
}

// Función para leer datos de la cámara térmica
// (Simulado - reemplazar con lectura real del sensor)
void readThermalData() {
    // En producción, esto leería del sensor AMG8833
    // Por ahora, simulamos datos realistas
    
    float baseTemp = 37.5;
    
    // Generar patrón térmico simulado
    for (int i = 0; i < SENSOR_ROWS; i++) {
        for (int j = 0; j < SENSOR_COLS; j++) {
            // Centro más caliente (simulando cuerpo del cerdo)
            float distance = sqrt(pow(i - 3.5, 2) + pow(j - 3.5, 2));
            float variation = 3.0 * exp(-distance / 2.0);
            thermalData[i][j] = baseTemp + variation + (random(-10, 10) / 100.0);
        }
    }
    
    ambientTemp = 22.0 + (random(-5, 5) / 100.0);
}

// Función para calcular estadísticas de temperatura
struct TempStats {
    float avgTemp;
    float maxTemp;
    float minTemp;
} calculateStats() {
    float sum = 0;
    float maxT = -100;
    float minT = 100;
    int count = 0;
    
    for (int i = 0; i < SENSOR_ROWS; i++) {
        for (int j = 0; j < SENSOR_COLS; j++) {
            sum += thermalData[i][j];
            maxT = max(maxT, thermalData[i][j]);
            minT = min(minT, thermalData[i][j]);
            count++;
        }
    }
    
    return {
        sum / count,      // Promedio
        maxT,             // Máximo
        minT              // Mínimo
    };
}

// Función para segmentar zonas corporales
// (Cabeza, Cuerpo, Patas)
JsonObject getZoneTemperatures(JsonObject zones) {
    // Zona de cabeza (esquina superior)
    float headSum = 0;
    for (int i = 0; i < 2; i++) {
        for (int j = 0; j < 2; j++) {
            headSum += thermalData[i][j];
        }
    }
    zones["head"]["avg_temp"] = headSum / 4.0;
    zones["head"]["max_temp"] = 38.5;
    
    // Zona de cuerpo (centro)
    float bodySum = 0;
    for (int i = 2; i < 6; i++) {
        for (int j = 2; j < 6; j++) {
            bodySum += thermalData[i][j];
        }
    }
    zones["body"]["avg_temp"] = bodySum / 16.0;
    zones["body"]["max_temp"] = 39.2;
    
    // Zona de patas (esquina inferior)
    float legsSum = 0;
    for (int i = 6; i < 8; i++) {
        for (int j = 6; j < 8; j++) {
            legsSum += thermalData[i][j];
        }
    }
    zones["legs"]["avg_temp"] = legsSum / 4.0;
    zones["legs"]["max_temp"] = 37.8;
    
    return zones;
}

// Función para enviar datos al servidor
void sendThermalData() {
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println(" WiFi desconectado");
        return;
    }
    
    // Leer datos
    readThermalData();
    TempStats stats = calculateStats();
    
    // Crear JSON
    StaticJsonDocument<1024> doc;
    doc["avg_temp"] = stats.avgTemp;
    doc["max_temp"] = stats.maxTemp;
    doc["min_temp"] = stats.minTemp;
    
    // Zonas térmicas
    JsonObject zones = doc.createNestedObject("zones");
    JsonObject head = zones.createNestedObject("head");
    JsonObject body = zones.createNestedObject("body");
    JsonObject legs = zones.createNestedObject("legs");
    
    head["avg_temp"] = stats.avgTemp - 0.5;
    head["max_temp"] = stats.maxTemp - 0.5;
    body["avg_temp"] = stats.avgTemp;
    body["max_temp"] = stats.maxTemp;
    legs["avg_temp"] = stats.avgTemp - 1.0;
    legs["max_temp"] = stats.maxTemp - 1.0;
    
    // Serializar JSON
    String payload;
    serializeJson(doc, payload);
    
    // Enviar POST
    http.begin(wifiClient, String(server) + "/api/thermal-data");
    http.addHeader("Content-Type", "application/json");
    
    int httpCode = http.POST(payload);
    
    if (httpCode == 200) {
        String response = http.getString();
        Serial.print(" Datos enviados. Respuesta: ");
        Serial.println(response);
        
        // Parsear respuesta
        StaticJsonDocument<256> responseDoc;
        deserializeJson(responseDoc, response);
        
        if (responseDoc["is_stressed"]) {
            Serial.print(" ESTRÉS DETECTADO: ");
            Serial.print(responseDoc["stress_level"].as<float>());
            Serial.println("%");
            triggerAlert();
        }
    } else {
        Serial.print(" Error HTTP: ");
        Serial.println(httpCode);
    }
    
    http.end();
}

// Función para activar alerta (buzzer, LED, etc.)
void triggerAlert() {
    // Activar buzzer si está conectado
    // digitalWrite(BUZZER_PIN, HIGH);
    // delay(500);
    // digitalWrite(BUZZER_PIN, LOW);
    
    // O encender LED de alerta
    // digitalWrite(LED_PIN, HIGH);
    
    Serial.println(" Enviando alerta de estrés al servidor");
}

// Setup
void setup() {
    Serial.begin(115200);
    delay(1000);
    
    Serial.println("\n\n ESP32-S3 Thermal Monitoring System");
    Serial.println("=====================================");
    
    // Inicializar pines
    // pinMode(BUZZER_PIN, OUTPUT);
    // pinMode(LED_PIN, OUTPUT);
    
    // Conectar a WiFi
    setupWiFi();
    
    // Inicializar cámara térmica
    setupThermalCamera();
    
    Serial.println("\n Sistema inicializado");
    Serial.print("Enviando datos cada ");
    Serial.print(SEND_INTERVAL / 1000);
    Serial.println(" segundos");
}

// Loop principal
void loop() {
    // Verificar conexión WiFi
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println(" Reconectando a WiFi...");
        setupWiFi();
    }
    
    // Enviar datos periódicamente
    if (millis() - lastSendTime >= SEND_INTERVAL) {
        lastSendTime = millis();
        sendThermalData();
    }
    
    delay(100);
}

/*
 * CONFIGURACIÓN:
 * 
 * 1. Reemplazar "YOUR_SSID" y "YOUR_PASSWORD" con tu WiFi
 * 2. Cambiar "localhost" por la IP de tu servidor Python
 * 3. Conectar sensor AMG8833:
 *    - VCC -> 3.3V
 *    - GND -> GND
 *    - SDA -> GPIO 21
 *    - SCL -> GPIO 22
 * 4. (Opcional) Conectar buzzer a GPIO 23 para alertas sonoras
 * 5. (Opcional) Conectar LED de alerta a GPIO 25
 * 
 * LIBRERÍAS REQUERIDAS:
 * - WiFi.h (incluida)
 * - HTTPClient.h (incluida)
 * - Wire.h (para I2C)
 * - ArduinoJson.h (instalar desde Arduino IDE)
 */

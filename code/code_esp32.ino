#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <WebSocketsClient.h>

// ==================== CONFIGURATION WiFi ====================
const char* ssid = "Redmi Note 13";        
const char* password = "ayouta123";         

// ==================== CONFIGURATION SERVEUR ====================
const char* serverIP = "192.168.1.100";     // À MODIFIER avec votre IP
const int serverPort = 5000;

// ==================== PINS DES CAPTEURS ====================
// Capteur ultrasonique (HC-SR04)
#define TRIG_PIN 5      // GPIO5
#define ECHO_PIN 18     // GPIO18

// Capteur de vibration (SW-420 ou similaire)
#define VIBRATION_PIN 34    // GPIO34 (entrée analogique)

// Capteur de pression (MPX5500DP ou similaire)
#define PRESSURE_PIN 35     // GPIO35 (entrée analogique)

// Vibreur d'alerte
#define VIBRATOR_PIN 23     // GPIO23

// ==================== PARAMÈTRES ====================
#define SENSOR_TIMEOUT 30000    // Timeout ultrason
const long sendInterval = 1000;  // Envoi toutes les 1 seconde

// WebSocket client
WebSocketsClient webSocket;
unsigned long lastSendTime = 0;

// ==================== FONCTIONS CAPTEURS ====================

// Lecture capteur ultrasonique (distance en cm)
float readUltrasonic() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  
  long duration = pulseIn(ECHO_PIN, HIGH, SENSOR_TIMEOUT);
  
  if (duration == 0) return -1;
  
  float distance = duration * 0.034 / 2;
  return distance;
}

// Lecture capteur vibration (0-4095 sur ESP32)
int readVibration() {
  int rawValue = analogRead(VIBRATION_PIN);
  // Convertir en mm/s (approximatif - à calibrer selon votre capteur)
  float vibration = map(rawValue, 0, 4095, 0, 100);
  return vibration;
}

// Lecture capteur pression (0-4095 sur ESP32)
float readPressure() {
  int rawValue = analogRead(PRESSURE_PIN);
  // Convertir en bar (approximatif - à calibrer selon votre capteur)
  float pressure = map(rawValue, 0, 4095, 0, 10);
  return pressure;
}

// ==================== FONCTIONS D'ENVOI ====================

// Envoi via HTTP POST (alternative plus simple)
void sendViaHTTP(float distance, int vibration, float pressure) {
  if (WiFi.status() != WL_CONNECTED) return;
  
  HTTPClient http;
  
  // URL de votre serveur Flask
  String url = "http://" + String(serverIP) + ":" + String(serverPort) + "/api/data";
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  
  // Créer le payload JSON
  StaticJsonDocument<256> doc;
  doc["vibration"] = vibration;
  doc["temperature"] = 25.0;  // Si vous avez un capteur de température
  doc["pression"] = pressure;
  doc["distance"] = distance;
  doc["device_id"] = "ESP32_001";
  doc["timestamp"] = millis();
  
  String payload;
  serializeJson(doc, payload);
  
  // Envoyer
  Serial.println("📤 Envoi HTTP: " + payload);
  int httpCode = http.POST(payload);
  
  if (httpCode > 0) {
    Serial.printf("✅ Réponse serveur: %d\n", httpCode);
    String response = http.getString();
    Serial.println("Réponse: " + response);
  } else {
    Serial.printf("❌ Erreur HTTP: %s\n", http.errorToString(httpCode).c_str());
  }
  
  http.end();
}

// Envoi via WebSocket (recommandé pour temps réel)
void sendViaWebSocket(float distance, int vibration, float pressure) {
  if (!webSocket.isConnected()) return;
  
  StaticJsonDocument<256> doc;
  doc["vibration"] = vibration;
  doc["temperature"] = 25.0;
  doc["pression"] = pressure;
  doc["distance"] = distance;
  doc["device_id"] = "ESP32_001";
  doc["timestamp"] = millis();
  
  String payload;
  serializeJson(doc, payload);
  
  Serial.println("📤 Envoi WebSocket: " + payload);
  webSocket.sendTXT(payload);
}

// ==================== CALLBACK WEBSOCKET ====================
void webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
  switch(type) {
    case WStype_DISCONNECTED:
      Serial.println("🔌 WebSocket déconnecté");
      break;
      
    case WStype_CONNECTED:
      Serial.println("🔌 WebSocket connecté au serveur");
      break;
      
    case WStype_TEXT:
      Serial.printf("📩 Message reçu: %s\n", payload);
      
      // Analyser la réponse JSON
      StaticJsonDocument<200> doc;
      deserializeJson(doc, payload);
      
      // Vérifier si le serveur demande d'activer le vibreur
      if (doc.containsKey("action") && doc["action"] == "activer_vibreur") {
        int duree = doc["duree"] | 1000;  // Durée par défaut: 1000ms
        Serial.printf("🔔 Activation vibreur pendant %d ms\n", duree);
        digitalWrite(VIBRATOR_PIN, HIGH);
        delay(duree);
        digitalWrite(VIBRATOR_PIN, LOW);
      }
      break;
  }
}

// ==================== SETUP ====================
void setup() {
  Serial.begin(115200);
  Serial.println("\n🚀 Démarrage ESP32 - Envoi données capteurs");
  
  // Initialisation des pins
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(VIBRATION_PIN, INPUT);
  pinMode(PRESSURE_PIN, INPUT);
  pinMode(VIBRATOR_PIN, OUTPUT);
  
  digitalWrite(TRIG_PIN, LOW);
  digitalWrite(VIBRATOR_PIN, LOW);
  
  // Connexion WiFi
  WiFi.begin(ssid, password);
  Serial.print("📡 Connexion WiFi");
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 40) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✅ WiFi connecté!");
    Serial.print("📡 Adresse IP: ");
    Serial.println(WiFi.localIP());
    
    // Connexion WebSocket
    Serial.println("🔌 Connexion au serveur WebSocket...");
    webSocket.begin(serverIP, serverPort, "/");
    webSocket.onEvent(webSocketEvent);
    webSocket.setReconnectInterval(5000);  // Reconnexion auto toutes les 5 secondes
    
  } else {
    Serial.println("\n❌ Échec connexion WiFi");
  }
}

// ==================== LOOP ====================
void loop() {
  // Gérer WebSocket
  webSocket.loop();
  
  // Envoyer les données à intervalle régulier
  unsigned long currentMillis = millis();
  if (currentMillis - lastSendTime >= sendInterval) {
    lastSendTime = currentMillis;
    
    // Lire les capteurs
    float distance = readUltrasonic();
    int vibration = readVibration();
    float pressure = readPressure();
    
    // Afficher dans le moniteur série
    Serial.println("\n📊 DONNÉES CAPTEURS:");
    Serial.printf("   📏 Distance: %.1f cm\n", distance);
    Serial.printf("   📳 Vibration: %d mm/s\n", vibration);
    Serial.printf("   📊 Pression: %.2f bar\n", pressure);
    
    // Envoyer au serveur (choisissez une méthode)
    if (webSocket.isConnected()) {
      sendViaWebSocket(distance, vibration, pressure);
    } else {
      sendViaHTTP(distance, vibration, pressure);
    }
  }
  
  delay(10);
}
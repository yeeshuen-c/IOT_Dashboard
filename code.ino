/*
  ESP32 publish telemetry data to VOne Cloud (Smart Kitchen)
*/

#include "VOneMqttClient.h"
#include "DHT.h"

// Define device IDs
const char* MQ2sensor = "ed7f6ce9-3bd2-4f6d-8dae-6d060f392c0f";    // Replace this with YOUR deviceID for the MQ2 sensor
const char* DHT11Sensor = "29099b40-50a8-457a-865f-5c120863cb15";  // Replace this with YOUR deviceID for the DHT11 sensor

// Used Pins
const int MQ2pin = A2;          // Middle Maker Port
const int dht11Pin = 4;         // Left side Maker Port
const int buzzerPin = 12;       // Onboard buzzer

// Input sensor
#define DHTTYPE DHT11
DHT dht(dht11Pin, DHTTYPE);

// Create an instance of VOneMqttClient
VOneMqttClient voneClient;

// Last message time
unsigned long lastMsgTime = 0;
float gasValue;

void setup_wifi() {
  delay(10);
  // We start by connecting to a WiFi network
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(WIFI_SSID);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());
}

void setup() {
  Serial.begin(115200);
  setup_wifi();
  voneClient.setup();
  Serial.println("Gas sensor warming up!");
  delay(20000);  // Allow the MQ-2 to warm up

  // Sensor
  dht.begin();

  // Actuator
  pinMode(buzzerPin, OUTPUT);
}

void loop() {
  if (gasValue > 2000) {
    tone(buzzerPin, 1000);
  } else {
    noTone(buzzerPin);
  }

  if (!voneClient.connected()) {
    voneClient.reconnect();
    voneClient.publishDeviceStatusEvent(MQ2sensor, true);
    voneClient.publishDeviceStatusEvent(DHT11Sensor, true);
  }
  voneClient.loop();

  unsigned long cur = millis();
  if (cur - lastMsgTime > INTERVAL) {
    lastMsgTime = cur;

    // Publish telemetry data
    gasValue = analogRead(MQ2pin);
    voneClient.publishTelemetryData(MQ2sensor, "Gas detector", gasValue);

    // Publish telemetry data 2
    float h = dht.readHumidity();
    int t = dht.readTemperature();

    JSONVar payloadObject;
    payloadObject["Humidity"] = h;
    payloadObject["Temperature"] = t;
    voneClient.publishTelemetryData(DHT11Sensor, payloadObject);
  }
}
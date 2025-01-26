/*
  ESP32 publish telemetry data to MQTT broker using TLS
*/

#include <WiFi.h>
#include <PubSubClient.h>
#include "DHT.h"
#include <WiFiClientSecure.h>  // Include the WiFiClientSecure library

#define DHTTYPE DHT11

// WiFi credentials
const char* WIFI_SSID = "ssid";           // Your WiFi SSID
const char* WIFI_PASSWORD = "password";   // Your WiFi password

// MQTT broker details
const char* MQTT_SERVER = "35.225.99.3";  // Your VM instance public IP address
const char* MQTT_TOPIC = "iot";           // MQTT topic for subscription
const int MQTT_PORT = 8883;               // TLS communication port

//CA certificate 
const char* CA_CERT = \
"-----BEGIN CERTIFICATE-----\n" \
"the CA cert in here but for security reasons, doesnt show when upload to repo\n" \
"-----END CERTIFICATE-----\n";

//client certificate 
const char* CLIENT_CERT = \
"-----BEGIN CERTIFICATE-----\n" \
"the client cert in here but for security reasons, doesnt show when upload to repo\n" \
"-----END CERTIFICATE-----\n";

//client key 
const char* CLIENT_KEY = \
"-----BEGIN PRIVATE KEY-----\n" \
"the client key in here but for security reasons, doesnt show when upload to repo\n" \
"-----END PRIVATE KEY-----\n";

//Sensor pins
const int dht11Pin = 4;                   // DHT11 sensor pin
const int MQ2pin = A2;                    // MQ2 sensor pin

//DHT sensor
DHT dht(dht11Pin, DHTTYPE);

//   WiFi and MQTT clients
WiFiClientSecure espClient;  // Use WiFiClientSecure for TLS
PubSubClient client(espClient);

//buffer for MQTT 
char buffer[128] = "";

//connect to WiFi
void setup_wifi() {
  delay(10);
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
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
}

//reconnect to MQTT broker
void reconnect() {
  while (!client.connected()) {
    Serial.println("Attempting MQTT connection...");

    if (client.connect("ESP32Client")) {
      Serial.println("Connected to MQTT server");
    } else {
      Serial.print("Failed, rc=");
      Serial.print(client.state());
      Serial.println(" Retrying in 5 seconds...");
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);                     // Initiate serial communication
  dht.begin();                              // Initialize DHT sensor
  setup_wifi();                             // Connect to the WiFi network

  //Set up the secure connection
  espClient.setCACert(CA_CERT);
  espClient.setCertificate(CLIENT_CERT);
  espClient.setPrivateKey(CLIENT_KEY);

  client.setServer(MQTT_SERVER, MQTT_PORT); // Set up the MQTT client
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }

  client.loop();
  delay(5000);

  //read temperature and humidity from DHT11 sensor
  float temperature = dht.readTemperature();
  float humidity = dht.readHumidity();

  //Read gas value from MQ2 sensor
  float gasValue = analogRead(MQ2pin);

  //   Publish temperature data
  sprintf(buffer, "Temperature: %.2f degree Celsius", temperature);
  client.publish(MQTT_TOPIC, buffer);
  Serial.println(buffer);

  //humidity data
  sprintf(buffer, "Humidity: %.2f%%", humidity);
  client.publish(MQTT_TOPIC, buffer);
  Serial.println(buffer);

  //gas value data
  sprintf(buffer, "Gas Value: %.2f", gasValue);
  client.publish(MQTT_TOPIC, buffer);
  Serial.println(buffer);
}
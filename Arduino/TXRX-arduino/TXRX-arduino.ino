#include <Arduino.h>
#include <SoftwareSerial.h>
SoftwareSerial Serial2(6,7);

void setup() {
  Serial.begin(9600); // Initialize primary serial for debugging
  Serial2.begin(9600); // Initialize Serial2 on GPIO16 (RX) and GPIO17 (TX)
}

void loop() {
  if (Serial.available()) {
    Serial.print("Uno Read ....");
    Serial.println(Serial2.read());
    Serial2.write(Serial.read()); // Forward data from primary serial to Serial2
  }
  if (Serial2.available()) {
    Serial.write(Serial2.read()); // Forward data from Serial2 to primary serial
  }
}
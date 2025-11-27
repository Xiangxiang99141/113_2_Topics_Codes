void setup() {
  Serial.begin(9600); // Initialize primary serial for debugging
  Serial2.begin(9600, SERIAL_8N1, 16, 17); // Initialize Serial2 on GPIO16 (RX) and GPIO17 (TX)
}

void loop() {
  if (Serial.available()) {
    Serial2.write(Serial.read()); // Forward data from primary serial to Serial2
  }
  // if (Serial2.available()) {
  //   Serial.write(Serial2.read()); // Forward data from Serial2 to primary serial
  // }
}
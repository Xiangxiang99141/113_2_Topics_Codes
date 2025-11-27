// #include <Arduino.h>
#include <Servo.h>

const int servoCount = 1;

static const int servosPins[servoCount] = {22} ;
Servo servos[servoCount];

void setServos(int degrees) {
    for(int i = 0; i < servoCount; ++i) {
        servos[i].write((degrees + (35 * i)) % 180);
    }
}


void setup() {
  // 1. 初始化電腦除錯用的 Serial (建議用 115200)
  Serial.begin(115200);
  Serial.println("Settiog Servo.....");
  Serial.println("ESP32 Servo Controller Started");
  for(int i = 0; i < servoCount; ++i) {
    if(!servos[i].attach(servosPins[i])) {
      Serial.print("Servo ");
      Serial.print(i);
      Serial.println("attach error");
    }else{
      Serial.println("Setting Servo ID : "+ i.toString());
    }
  }
}

void loop() {
    for(int posDegrees = 0; posDegrees <= 180; posDegrees++) {
      setServos(posDegrees);
      Serial.println(posDegrees);
      delay(20);
    }

    for(int posDegrees = 180; posDegrees >= 0; posDegrees--) {
      setServos(posDegrees);
      Serial.println(posDegrees);
      delay(20);
    }
    delay(2000);
}
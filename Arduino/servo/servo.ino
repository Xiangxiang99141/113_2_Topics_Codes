
// #include <Arduino.h>
#include <LobotServoController.h>

SoftwareSerial Serial1(2, 3);
SoftwareSerial ESP32Serial(6, 7);
LobotServoController myse(Serial1); //將Arduino Pin2設定為RX, Pin3設定為TX

void setup() {
  pinMode(13,OUTPUT);
  Serial1.begin(9600);
  Serial.begin(9600);
  ESP32Serial.begin(9600);
  while(!Serial1);
  digitalWrite(13,HIGH);
}



void actionGroup(){
  Serial.println("balance....");
  LobotServo servos1[2];   //an array of struct LobotServo
  servos1[0].ID = 0;       //No.1 servo
  servos1[0].Position = 1500;  //1400 position
  // servos1[1].ID = 3;       //No.4 servo
  // servos1[1].Position = 1737;  //700 position
  servos1[1].ID = 15;       //No.4 servo
  servos1[1].Position = 1500;  //700 position
  myse.moveServos(servos1,2,2000);  //control 2 servos, action time is 1000ms, ID and position are specified by the structure array "servos"
  delay(2000);
  myse.moveServos(servos1,2,6000);  //control 2 servos, action time is 1000ms, ID and position are specified by the structure array "servos"
  delay(6000);

  servos1[0].Position = 2000;  //1400 position
  servos1[1].Position = 1000;  //700 position
  // servos1[2].Position = 1300;  //700 position

  myse.moveServos(servos1,2,1000);
  digitalWrite(13,HIGH);
  delay(2000);
}

void loop() {
  // Serial.write(ESP32Serial.read()); // Forward data from Serial2 to primary serial
  if(ESP32Serial.available()){
    String msg = ESP32Serial.readString();
    msg.trim();
    Serial.println("msg:" + msg);
    if(msg == "turn"){
        actionGroup();
    }else{
      Serial.println("error:"+msg);
    }
  }
}

// void loop(){
//   actionGroup();
// }

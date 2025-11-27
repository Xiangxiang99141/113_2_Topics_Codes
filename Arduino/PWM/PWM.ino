#include <ESP32Servo.h>

const int servosCount = 2;

// int APin = 13;
// int BPin = 14;
int pins[servosCount] = {13,14};
Servo servo[servosCount];
// 儲存目前角度的變數
int pos = 0;
void setup() {
	// Allow allocation of all timers
	ESP32PWM::allocateTimer(0);
	ESP32PWM::allocateTimer(1);
	ESP32PWM::allocateTimer(2);
	ESP32PWM::allocateTimer(3);
	Serial.begin(115200);

  for(int i=0;i<servosCount;++i){
    servo[i].setPeriodHertz(50);
    servo[i].attach(pins[i], 500, 2400); // 1KHz 10 bits
  }
	// pwm.attachPin(BPin, freq, 10); // 1KHz 10 bits
  servo[0].write(0);
  servo[1].write(180);
}
void loop() {
  // --- 動作 1: 從 0 度轉到 180 度 ---
    Serial.println("Moving: 0 -> 180");
    for (pos = 0; pos <= 180; pos += 1) { 
        // 馬達 1：正向跟隨 pos
        servo[0].write(pos);              
        
        // 馬達 2：反向 (總角度 - 目前角度)
        servo[1].write(180 - pos);        
        
        delay(15); // 控制轉動速度，數值越小轉越快
    }
    
    delay(1000); // 到達極限後暫停 1 秒

    // --- 動作 2: 從 180 度轉回 0 度 ---
    Serial.println("Moving: 180 -> 0");
    for (pos = 180; pos >= 0; pos -= 1) { 
        // 馬達 1：正向跟隨 pos
        servo[0].write(pos);              
        
        // 馬達 2：反向
        servo[1].write(180 - pos);        
        
        delay(15);
    }

    delay(1000); // 回到原點後暫停 1 秒
}

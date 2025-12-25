/*esp32-lsc16 ok */
#include <Arduino.h>
#include <Wire.h>
#include <WiFi.h>
#include <WiFiManager.h>       
#include <WiFiClientSecure.h>
#include <WebSocketsClient.h>
#include <ArduinoJson.h>
#include <Preferences.h>   // <<<<<< 新增
#define RXD2 16
#define TXD2 17

// LSC-16 二進位協議常數
#define FRAME_HEADER            0x55
#define CMD_SERVO_MOVE          0x03



// [NEW] 請在此設定您的 WebSocket 伺服器位址
// ==============================================================
WebSocketsClient webSocket;
char  WS_HOST[40] = "192.168.0.16";
int   WS_PORT = 8080;
const char* WS_PATH = "";                       // 伺服器上的路徑
// ==============================================================

Preferences prefs;  // <<<<<< 新增

//arduinoJson
// ==============================================================
JsonDocument doc;
// ==============================================================


// 定義一個結構來存放馬達資訊
struct LobotServo {
  uint8_t  ID;       // 馬達編號
  uint16_t Position; // 目標位置
};

//函數初始話
void webSocketEvent(WStype_t ,uint8_t* ,size_t);
void moveServos(LobotServo[], uint8_t, uint16_t);
void ActionGroup();
void resetAction();

void setup() {
  Serial.begin(115200);
  Serial2.begin(9600, SERIAL_8N1, RXD2, TXD2);
  resetAction();\
  WiFiManager wm;
  wm.setConfigPortalTimeout(180);

  // --- 先讀取已保存的 WS 設定 ---
  prefs.begin("smartscale", false);
  String savedHost = prefs.getString("ws_host", "192.168.0.16");
  int savedPort    = prefs.getInt("ws_port", 8080);
  strlcpy(WS_HOST, savedHost.c_str(), sizeof(WS_HOST));
  WS_PORT = savedPort;

  // 加入可輸入 WS Host/IP 與 Port
  WiFiManagerParameter p_ws_host("ws_host", "WS Host / IP", WS_HOST, 39);
  char portBuf[8];
  snprintf(portBuf, sizeof(portBuf), "%d", WS_PORT);
  WiFiManagerParameter p_ws_port("ws_port", "WS Port", portBuf, 7);
  wm.addParameter(&p_ws_host);
  wm.addParameter(&p_ws_port);

  //開器設定wifi 網頁;
  if(!wm.autoConnect("Motor-ESP32","12345678")){
    Serial.println("AP:Motor-ESP32");
    Serial.println("PW:12345678");
  }
  
  Serial.println("WiFi Connected!");
  delay(1000);
  
  // 既然您測試成功的是這一段，請保持 9600
  // Serial.print("Connect Ws:");
  // 取回使用者輸入 + 防呆 + 存入 NVS
  strlcpy(WS_HOST, p_ws_host.getValue(), sizeof(WS_HOST));
  WS_PORT = atoi(p_ws_port.getValue());

  if (strlen(WS_HOST) == 0) strlcpy(WS_HOST, "192.168.0.16", sizeof(WS_HOST));
  if (WS_PORT <= 0 || WS_PORT > 65535) WS_PORT = 8080;

  prefs.putString("ws_host", WS_HOST);
  prefs.putInt("ws_port", WS_PORT);
  prefs.end();
  Serial.printf("Using WS_HOST=%s, WS_PORT=%d\n", WS_HOST, WS_PORT);
  
  webSocket.begin(WS_HOST, WS_PORT, WS_PATH);

  // 註冊事件處理函式
  webSocket.onEvent(webSocketEvent);
  // 設定自動重連間隔 (例如 5000ms)
  webSocket.setReconnectInterval(5000);
  // 建立網路任務 (與前版相同，但任務內容已不同)
  // xTaskCreatePinnedToCore(networkTask, "Network Task", 8192, NULL, 1, NULL, 0);

  Serial.println("Action Group Started (Binary Protocol)...");
  delay(1000);
}

// ---------------------------------------------------------
// 核心功能：一次控制多個馬達 (翻譯成二進位碼)
// ---------------------------------------------------------
void moveServos(LobotServo servos[], uint8_t Num, uint16_t Time) {
  uint8_t buf[128]; // 緩衝區

  if (Num > 32) Num = 32; // 限制最大數量
  if (Time < 0) Time = 0;

  // 1. 建立封包頭
  buf[0] = FRAME_HEADER;  // 0x55
  buf[1] = FRAME_HEADER;  // 0x55
  buf[2] = Num * 3 + 5;   // 資料長度 (每個馬達3bytes + 5個固定bytes)
  buf[3] = CMD_SERVO_MOVE;// 指令 0x03
  buf[4] = Num;           // 馬達數量
  buf[5] = (uint8_t)(Time & 0xFF);        // 時間低位
  buf[6] = (uint8_t)((Time >> 8) & 0xFF); // 時間高位

  // 2. 填入每個馬達的 ID 和 位置
  uint8_t index = 7;
  for (uint8_t i = 0; i < Num; i++) {
    buf[index++] = servos[i].ID;
    buf[index++] = (uint8_t)(servos[i].Position & 0xFF);
    buf[index++] = (uint8_t)((servos[i].Position >> 8) & 0xFF);
  }

  // 3. 發送二進位資料
  Serial2.write(buf, buf[2] + 2);
  
  Serial.printf("Sent Group Move: %d Servos, Time %d ms\n", Num, Time);
}

void ActionGroup(){
  // LobotServo step1[] = { {0, 1500}, {3, 1500}, {15, 1500} };
  // moveServos(step1, 3, 3000);
  // delay(3000); // 等待動作完成

  // --- 動作 2 (對應截圖 Index 2) ---
  // 時間: 1000ms
  // ID0->1500, ID3->1752, ID15->1500
  LobotServo step2[] = { {0, 1500}, {3, 1752}, {15, 1500} };
  moveServos(step2, 3, 1000);
  delay(1000);

  // --- 動作 3 (對應截圖 Index 3) ---
  // 時間: 2500ms
  // 位置不變 (停留等待)，但我們還是發送指令鎖定位置
  LobotServo step3[] = { {0, 1500}, {3, 1752}, {15, 1500} };
  moveServos(step3, 3, 4500);
  delay(4500);
  LobotServo step4[] = { {0, 1500}, {3, 1500}, {15, 1500} };
  moveServos(step4, 3, 500);
  delay(500);

  // --- 動作 4 (對應截圖 Index 4) ---
  // 時間: 1500ms
  // ID0->2000, ID3->1511, ID15->1000
  LobotServo step5[] = { {0, 2000}, {3, 1511}, {15, 1000} };
  moveServos(step5, 3, 1500);
  delay(1500);
}
//歸零
void resetAction(){
  LobotServo step1[] = { {0, 1500}, {3, 1500}, {15, 1500} };
  moveServos(step1, 3, 3000);
  delay(3000); // 等待動作完成
}


// ==================== [ NEW ] ====================
// [NEW] WebSocket 事件處理函式
void webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
  switch (type) {
    case WStype_DISCONNECTED:
      Serial.printf("[WSc] Disconnected!\n");
      break;
    case WStype_CONNECTED:
      Serial.printf("[WSc] Connected to url: %s\n", payload);
      break;
    case WStype_TEXT:
      Serial.printf("[WSc] get text: %s\n", payload);
      Serial.println("Desrializing payload");
      deserializeJson(doc, payload);
      // [可選] 在這裡處理從伺服器收到的指令
      if(doc["type"] == "weight" && doc["p"] == "master"){
        Serial.println("Master send weight");
        String data = doc["data"].as<String>();
        if(data.toInt()>0){
          ActionGroup();
        }else if(data.toInt()<=0){
          resetAction();
        }
      }
      /*
        "type": "weight",
        "data": "00.0",
        "p": "master"
      */

      break;
    case WStype_BIN:
      Serial.printf("[WSc] get binary length: %u\n", length);
      break;
    case WStype_ERROR:
    case WStype_FRAGMENT_TEXT_START:
    case WStype_FRAGMENT_BIN_START:
    case WStype_FRAGMENT:
    case WStype_FRAGMENT_FIN:
      break;
  }
}

void loop() {
  webSocket.loop();
  // // --- 動作 1 (對應截圖 Index 1) ---
  // // 時間: 3000ms
  // // ID0->1500, ID3->1500, ID15->1500
  // LobotServo step1[] = { {0, 1500}, {12, 1500}, {15, 1500} };
  // moveServos(step1, 3, 3000);
  // delay(3000); // 等待動作完成

  // // --- 動作 2 (對應截圖 Index 2) ---
  // // 時間: 1000ms
  // // ID0->1500, ID3->1752, ID15->1500
  // LobotServo step2[] = { {0, 1500}, {12, 1752}, {15, 1500} };
  // moveServos(step2, 3, 1000);
  // delay(1000);

  // // --- 動作 3 (對應截圖 Index 3) ---
  // // 時間: 2500ms
  // // 位置不變 (停留等待)，但我們還是發送指令鎖定位置
  // LobotServo step3[] = { {0, 1500}, {12, 1752}, {15, 1500} };
  // moveServos(step3, 3, 2500);
  // delay(2500);

  // // --- 動作 4 (對應截圖 Index 4) ---
  // // 時間: 1500ms
  // // ID0->2000, ID3->1511, ID15->1000
  // LobotServo step4[] = { {0, 2000}, {12, 1511}, {15, 1000} };
  // moveServos(step4, 3, 1500);
  // delay(1500);

  // 動作結束，休息一下重跑
}
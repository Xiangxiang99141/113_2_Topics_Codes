/*
   test ok - WebSocket 版本

*/

#include <Arduino.h>
#include <Wire.h>
#include <WiFi.h>
#include <WiFiManager.h>       
#include <WiFiClientSecure.h>
#include <WebSocketsClient.h>

#include "HX711.h"
#include <LiquidCrystal_I2C.h>

#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <freertos/queue.h>



// [NEW] 請在此設定您的 WebSocket 伺服器位址
// ==============================================================
const char* WS_HOST = "192.168.50.48";
const int   WS_PORT = 8080;
const char* WS_PATH = "";                       // 伺服器上的路徑
// ==============================================================

WebSocketsClient webSocket;
const int HX_DT_PIN         = 23;
const int HX_SCK_PIN        = 18;
const int I2C_SDA           = 21;
const int I2C_SCL           = 22;
const int BTN_PIN           = 14;
const int WIFI_LED          = 2;
const float         CAL_WEIGHT_G             = 100.0f;
const unsigned long WAIT_PUT_TIMEOUT_MS      = 20000;
const long          PLACE_DETECT_THRESHOLD_RAW = 8000;
const long          CAL_RAW_STABILITY_THRESHOLD = 100;
LiquidCrystal_I2C lcd(0x27, 16, 2);
const unsigned long SAMPLE_PERIOD_MS   = 30;
const unsigned long DISPLAY_PERIOD_MS  = 80;
const unsigned long UPLOAD_TICK_MS     = 250;
const unsigned long WIFI_TICK_MS       = 1000;
unsigned long tSample = 0, tDisplay = 0, tUploadTick = 0, tWiFi = 0;
const float ALPHA = 0.60f;
const float DISPLAY_DEADBAND_G = 0.10f;
float gEMA = 0.0f;
float lastShownWeight = 1e9;
struct StabilityTracker {
  constexpr static int WINDOW_SIZE = 12;
  constexpr static float SD_THRESHOLD_G = 0.50f;
  const static unsigned long DWELL_MS = 400;
  float ring_buffer[WINDOW_SIZE];
  int pos = 0, count = 0;
  bool isStable = false, wasStable = false;
  unsigned long stableSince = 0;
};
StabilityTracker stability;
struct UploadManager {
  const static unsigned long COOLDOWN_MS = 2000;
  constexpr static float MIN_RECORD_DELTA_G = 3.0f;
  constexpr static float MIN_VALID_G = 50.0f;
  constexpr static float ZERO_DETECT_THRESHOLD_G = 10.0f;
  unsigned long lastUploadAt = 0;
  float lastUploadedWeight = -1e9;
};
UploadManager uploader;
struct Button {
  const static unsigned long LONG_PRESS_MS = 2000;
  const static unsigned long SHORT_MAX_MS = 700;
  bool wasLow = false;
  unsigned long downAt = 0;
};
Button button;
QueueHandle_t uploadQueue;
HX711 scale;
bool isCalibrated = false;
float scaleFactor = 1.0f;

// ---------- 小工具 & LCD 顯示 (與前版相同) ----------
static inline float median3(float a, float b, float c) {
  if (a > b) {
    float t = a;
    a = b;
    b = t;
  } if (b > c) {
    float t = b;
    b = c;
    c = t;
  } if (a > b) {
    float t = a;
    a = b;
    b = t;
  } return b;
}
static inline float mean(const float* x, int n) {
  double s = 0;
  for (int i = 0; i < n; i++) s += x[i];
  return (n > 0) ? (s / n) : 0;
}
static inline float stdev(const float* x, int n, float m) {
  if (n < 2) return 1e9;
  double s = 0;
  for (int i = 0; i < n; i++) {
    double d = x[i] - m;
    s += d * d;
  } return sqrt(s / (n - 1));
}
void ledUpdate() {
  digitalWrite(WIFI_LED, (WiFi.status() == WL_CONNECTED) ? HIGH : LOW);
}
void lcdFrame() {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Weight:        g");
  lcd.setCursor(0, 1);
  lcd.print("WiFi:? STB:?      ");
}
void lcdSetWeight(float g) {
  lcd.setCursor(8, 0);
  char buf[7];
  snprintf(buf, sizeof(buf), "%6.1f", g);
  lcd.print(buf);
}
void lcdSetStatus() {
  lcd.setCursor(5, 1);  // [MODIFIED] WiFi 狀態顯示 WS
  if (WiFi.status() != WL_CONNECTED) lcd.print(".. ");
  else lcd.print(webSocket.isConnected() ? "WS " : "OK ");
  lcd.setCursor(11, 1);
  lcd.print(stability.isStable ? "Y " : "N ");
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
      // [可選] 在這裡處理從伺服器收到的指令
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


// ===========================================================
// ---------- 網路任務 (WebSocket 版本 - 新JSON格式 - 使用 dtostrf) ----------

void networkTask(void *pvParameters) {
  float weightToUpload; // 從佇列接收 100.0f
  const TickType_t xQueueTimeout = pdMS_TO_TICKS(50);
  char weightString[10];

  for (;;) {
    webSocket.loop();


    if (xQueueReceive(uploadQueue, &weightToUpload, xQueueTimeout)) {

      if (webSocket.isConnected()) {

        // 1. [關鍵修正]
        // 使用 dtostrf 將 float 轉換為字串 (最可靠)
        // 參數: (float變數, 最小總寬度, 小數點後幾位, 儲存的char陣列)
        // 範例: weightToUpload = 100.0
        dtostrf(weightToUpload, 4, 1, weightString);
        // 結果: weightString 變數現在會是 "100.0"

        // 2. [關鍵修正]
        // 使用 %s (字串) 來組合 payload
        char payload[100];
        snprintf(payload, sizeof(payload),
                 "{\"p\":\"master\",\"type\":\"W\", \"data\":\"%s\"}",
                 weightString); // <-- 改成 %s 並使用 weightString

        // 透過 WebSocket 發送
        webSocket.sendTXT(payload);

        Serial.printf("WebSocket SENT: %s\n", payload);
      } else {
        Serial.println("WebSocket disconnected. Data dropped.");
      }
    }
  }
}

// ---------- 校正程序 (與前版相同) ----------
bool runCalibration() {
  scale.set_scale(1.0f); lcd.clear(); lcd.setCursor(0, 0); lcd.print("Tare... Empty"); scale.tare();
  int stableBatches = 0; long lastMean = LONG_MIN;
  while (stableBatches < 10) {
    long s = 0;
    for (int i = 0; i < 10; i++) {
      s += scale.get_value(1);
      delay(8);
    } long m = s / 10;
    if (lastMean == LONG_MIN || labs(m - lastMean) <= CAL_RAW_STABILITY_THRESHOLD) stableBatches++;
    else stableBatches = 0;
    lastMean = m;
  }
  lcd.clear(); lcd.setCursor(0, 0); lcd.print("Put 100g..."); unsigned long t0 = millis();
  while (millis() - t0 < WAIT_PUT_TIMEOUT_MS) {
    if (labs(scale.get_value(5)) > PLACE_DETECT_THRESHOLD_RAW) break;
    delay(30);
  }
  lcd.setCursor(0, 1); lcd.print("Reading...      ");
  stableBatches = 0; lastMean = LONG_MIN; long raw100 = 0;
  while (stableBatches < 10) {
    long s = 0;
    for (int i = 0; i < 10; i++) {
      s += scale.get_value(1);
      delay(8);
    } long m = s / 10;
    if (lastMean == LONG_MIN || labs(m - lastMean) <= CAL_RAW_STABILITY_THRESHOLD) stableBatches++;
    else stableBatches = 0;
    lastMean = m;
    if (stableBatches >= 10) {
      raw100 = m;
      break;
    }
  }
  float factor = (float)raw100 / CAL_WEIGHT_G;
  if (!isfinite(factor) || fabs(factor) < 1e-3f) {
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Cal Failed");
    delay(800);
    return false;
  }
  scaleFactor = factor; scale.set_scale(scaleFactor);
  if (scale.get_units(10) < 0) {
    scaleFactor = -scaleFactor;
    scale.set_scale(scaleFactor);
  }
  lcd.clear(); lcd.setCursor(0, 0); lcd.print("Cal OK"); delay(500);
  return true;
}

// ... (resetMeasurementState 和 handleButton 與前版相同) ...
void resetMeasurementState() {
  stability.pos = stability.count = 0;
  stability.stableSince = 0;
  stability.isStable = stability.wasStable = false;
  gEMA = 0;
  lastShownWeight = 1e9;
}
void handleButton() {
  int lv = digitalRead(BTN_PIN);
  if (lv == LOW && !button.wasLow) {
    button.wasLow = true;
    button.downAt = millis();
  }
  else if (lv == HIGH && button.wasLow) {
    unsigned long dur = millis() - button.downAt; button.wasLow = false;
    if (dur >= Button::LONG_PRESS_MS) {
      isCalibrated = false;
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Calibrating...");
      if (runCalibration()) isCalibrated = true;
      resetMeasurementState();
      lcdFrame();
      lcdSetStatus();
    }
    else if (dur <= Button::SHORT_MAX_MS) {
      scale.tare();
      resetMeasurementState();
      lcd.setCursor(0, 1);
      lcd.print("Tare            ");
      delay(200);
      lcdSetStatus();
    }
  }
}

// ================= Setup / Loop =================
void setup() {
  pinMode(BTN_PIN, INPUT_PULLUP); pinMode(WIFI_LED, OUTPUT); digitalWrite(WIFI_LED, LOW);
  Serial.begin(115200);
  Wire.begin(I2C_SDA, I2C_SCL); Wire.setClock(400000);
  lcd.init(); lcd.backlight(); lcd.clear(); lcd.setCursor(0, 0); lcd.print("Booting...");

  // --- WiFiManager (與前版相同) ---
  WiFiManager wm;
  wm.setConfigPortalTimeout(180);
  lcd.clear(); lcd.setCursor(0, 0); lcd.print("Config WiFi...");
  lcd.setCursor(0, 1); lcd.print("AP: SmartScale");

  if (!wm.autoConnect("SmartScale-Config")) {
    Serial.println("Failed to connect and hit timeout");
    lcd.clear(); lcd.print("WiFi Failed");
    delay(3000);
    ESP.restart();
  }

  Serial.println("WiFi Connected!");
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Wifi is connect");
  delay(1000);
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Please connect");
  lcd.setCursor(0, 1);
  lcd.print("Weight Sensor");
  
  // -------------------

  // [NEW] WiFi 連線成功後，設定並啟動 WebSocket
  // ===============================================
  if (WS_PORT == 443) {
    // 使用 WSS (安全的 WebSocket)
    webSocket.beginSSL(WS_HOST, WS_PORT, WS_PATH);
    // [可選] 如果您的 WSS 伺服器使用自簽憑證，請取消註解下一行
    // webSocket.setInsecure();
  } else {
    // 使用 WS (不安全的 WebSocket)
    webSocket.begin(WS_HOST, WS_PORT, WS_PATH);
  }

  // 註冊事件處理函式
  webSocket.onEvent(webSocketEvent);
  // 設定自動重連間隔 (例如 5000ms)
  webSocket.setReconnectInterval(5000);
  // ===============================================

  scale.begin(HX_DT_PIN, HX_SCK_PIN); scale.set_scale(1.0f); scale.tare();
  if (runCalibration()) isCalibrated = true;

  uploadQueue = xQueueCreate(5, sizeof(float));

  // 建立網路任務 (與前版相同，但任務內容已不同)
  xTaskCreatePinnedToCore(networkTask, "Network Task", 8192, NULL, 1, NULL, 0);

  lcdFrame(); lcdSetStatus();
  unsigned long now = millis();
  tSample = tDisplay = tUploadTick = tWiFi = now;
}

// loop 迴圈完全不變
void loop() {
  unsigned long now = millis();
  handleButton();
  if (now - tWiFi >= WIFI_TICK_MS) {
    ledUpdate();  // (webSocket.loop() 已移至 networkTask)
    tWiFi = now;
  }
  if (!isCalibrated) {
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Calibrating...");
    delay(120);
    return;
  }

  // 1) 取樣
  if (now - tSample >= SAMPLE_PERIOD_MS) {
    float gMed = median3(scale.get_units(), scale.get_units(), scale.get_units());
    gEMA = ALPHA * gMed + (1.0f - ALPHA) * gEMA;
    stability.ring_buffer[stability.pos] = gEMA;
    stability.pos = (stability.pos + 1) % StabilityTracker::WINDOW_SIZE;
    if (stability.count < StabilityTracker::WINDOW_SIZE) stability.count++;
    tSample = now;
  }

  // 2) 穩定判定
  if (stability.count >= StabilityTracker::WINDOW_SIZE) {
    float m = mean(stability.ring_buffer, StabilityTracker::WINDOW_SIZE);
    float sd = stdev(stability.ring_buffer, StabilityTracker::WINDOW_SIZE, m);
    bool sd_ok = (sd <= StabilityTracker::SD_THRESHOLD_G);
    if (sd_ok) {
      if (stability.stableSince == 0) stability.stableSince = now;
      stability.isStable = (now - stability.stableSince >= StabilityTracker::DWELL_MS);
    }
    else {
      stability.stableSince = 0;
      stability.isStable = false;
    }
  }

  // 3) 顯示
  if (now - tDisplay >= DISPLAY_PERIOD_MS) {
    if (fabs(gEMA - lastShownWeight) >= DISPLAY_DEADBAND_G) {
      lastShownWeight = gEMA;
      lcdSetWeight(lastShownWeight);
    }
    lcdSetStatus(); // 現在會顯示 "WS" 狀態
    tDisplay = now;
  }

  // 4) 上傳邏輯 ( [MODIFIED] 新增零點偵測 )
  if(now - tUploadTick >= UPLOAD_TICK_MS){
    bool becameStable = (!stability.wasStable && stability.isStable);
    bool cooldownOK   = (now - uploader.lastUploadAt >= UploadManager::COOLDOWN_MS);

    // --- 判斷兩種觸發條件 ---

    // 條件 1: 偵測到有效 (重) 的物體 (>50g)
    bool isHeavyWeight = (fabs(lastShownWeight) >= UploadManager::MIN_VALID_G);
    bool isBigChange = (fabs(lastShownWeight - uploader.lastUploadedWeight) >= UploadManager::MIN_RECORD_DELTA_G);
    
    bool sendHeavyWeight = becameStable && cooldownOK && isHeavyWeight && isBigChange;

    // 條件 2: 偵測到零點 (<10g) 
    // 並且 [前一次上傳] 是重的 (>=10g)，避免重複發送0
    bool isLightWeight = (fabs(lastShownWeight) < UploadManager::ZERO_DETECT_THRESHOLD_G);
    bool wasLastWeightHeavy = (uploader.lastUploadedWeight >= UploadManager::ZERO_DETECT_THRESHOLD_G); 
    
    bool sendZeroWeight = becameStable && cooldownOK && isLightWeight && wasLastWeightHeavy;

    // --- 執行上傳 ---
    
    float weightToSend = 0.0f;
    bool shouldSend = false;

    if (sendHeavyWeight) {
        // 發送實際重量 (例如 65.5)
        weightToSend = lastShownWeight; 
        shouldSend = true;
    } else if (sendZeroWeight) {
        // 發送固定的 0.0
        weightToSend = 0.0f;
        shouldSend = true;
    }

    // 如果任一條件滿足，就發送到佇列
    if (shouldSend) {
      if (xQueueSend(uploadQueue, &weightToSend, (TickType_t)0) == pdPASS) {
        uploader.lastUploadAt = now;
        uploader.lastUploadedWeight = weightToSend; // 關鍵：更新最後上傳的值 (會變成 0.0)
        lcd.setCursor(11,1); lcd.print("Y*");
      }
    }
    
    stability.wasStable = stability.isStable;
    tUploadTick = now;
  }// 4) 上傳邏輯 ( [MODIFIED] 新增零點偵測 )
  if(now - tUploadTick >= UPLOAD_TICK_MS){
    bool becameStable = (!stability.wasStable && stability.isStable);
    bool cooldownOK   = (now - uploader.lastUploadAt >= UploadManager::COOLDOWN_MS);

    // --- 判斷兩種觸發條件 ---

    // 條件 1: 偵測到有效 (重) 的物體 (>50g)
    bool isHeavyWeight = (fabs(lastShownWeight) >= UploadManager::MIN_VALID_G);
    bool isBigChange = (fabs(lastShownWeight - uploader.lastUploadedWeight) >= UploadManager::MIN_RECORD_DELTA_G);
    
    bool sendHeavyWeight = becameStable && cooldownOK && isHeavyWeight && isBigChange;

    // 條件 2: 偵測到零點 (<10g) 
    // 並且 [前一次上傳] 是重的 (>=10g)，避免重複發送0
    bool isLightWeight = (fabs(lastShownWeight) < UploadManager::ZERO_DETECT_THRESHOLD_G);
    bool wasLastWeightHeavy = (uploader.lastUploadedWeight >= UploadManager::ZERO_DETECT_THRESHOLD_G); 
    
    bool sendZeroWeight = becameStable && cooldownOK && isLightWeight && wasLastWeightHeavy;

    // --- 執行上傳 ---
    
    float weightToSend = 0.0f;
    bool shouldSend = false;

    if (sendHeavyWeight) {
        // 發送實際重量 (例如 65.5)
        weightToSend = lastShownWeight; 
        shouldSend = true;
    } else if (sendZeroWeight) {
        // 發送固定的 0.0
        weightToSend = 0.0f;
        shouldSend = true;
    }

    // 如果任一條件滿足，就發送到佇列
    if (shouldSend) {
      if (xQueueSend(uploadQueue, &weightToSend, (TickType_t)0) == pdPASS) {
        uploader.lastUploadAt = now;
        uploader.lastUploadedWeight = weightToSend; // 關鍵：更新最後上傳的值 (會變成 0.0)
        lcd.setCursor(11,1); lcd.print("Y*");
      }
    }
    
    stability.wasStable = stability.isStable;
    tUploadTick = now;
  }
}

#include <Arduino.h>
#include <Wire.h>
#include <WiFi.h>
#include <WiFiManager.h>  // <--- 引入 WiFiManager 函式庫
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include "HX711.h"
#include <LiquidCrystal_I2C.h>

#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <freertos/queue.h>

// ===== Wi-Fi / Apps Script =====
// 不再需要 SSID 和 PASSWORD 常數
const char* SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyMFTqwwHlFBnpjyqw4sYIvh3HwqWvPsjTXDNhiN3dMhPZk6J73LlWi27dlnRNof-f8/exec";

// ===== 硬體腳位 (與前版相同) =====
const int HX_DT_PIN = 23;
const int HX_SCK_PIN = 18;
const int I2C_SDA = 21;
const int I2C_SCL = 22;
const int BTN_PIN = 14;
const int WIFI_LED = 2;

// ===== 校正參數 (與前版相同) =====
const float CAL_WEIGHT_G = 100.0f;
const unsigned long WAIT_PUT_TIMEOUT_MS = 20000;
const long PLACE_DETECT_THRESHOLD_RAW = 8000;
const long CAL_RAW_STABILITY_THRESHOLD = 100;

// ===== LCD 16×2 (與前版相同) =====
LiquidCrystal_I2C lcd(0x3f, 16, 2);

// ===== 排程 (與前版相同) =====
const unsigned long SAMPLE_PERIOD_MS = 30;
const unsigned long DISPLAY_PERIOD_MS = 80;
const unsigned long UPLOAD_TICK_MS = 250;
const unsigned long WIFI_TICK_MS = 1000;
unsigned long tSample = 0, tDisplay = 0, tUploadTick = 0, tWiFi = 0;

// ===== 其餘結構體與變數宣告 (與前版相同) =====
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
  constexpr static float MIN_VALID_G = 40.0f;
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
  }
  if (b > c) {
    float t = b;
    b = c;
    c = t;
  }
  if (a > b) {
    float t = a;
    a = b;
    b = t;
  }
  return b;
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
  }
  return sqrt(s / (n - 1));
}
void ledUpdate() {
  digitalWrite(WIFI_LED, (WiFi.status() == WL_CONNECTED) ? HIGH : LOW);
}
void lcdFrame() {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Weight:        g");
  lcd.setCursor(0, 1);
  lcd.print("WiFi:? STB:?     ");
}
void lcdSetWeight(float g) {
  lcd.setCursor(8, 0);
  char buf[7];
  snprintf(buf, sizeof(buf), "%6.1f", g);
  lcd.print(buf);
}
void lcdSetStatus() {
  lcd.clear();
  lcd.setCursor(0, 0);
  if (WiFi.status() != WL_CONNECTED){
    Serial.println("3");
    lcd.print(".. ");
  }
  else {
    Serial.println(WiFi.localIP());
    lcd.print(WiFi.localIP().toString());
  };
  lcd.setCursor(7, 1);
  lcd.print(stability.isStable ? "Y " : "N ");
}

// ==================== [ 修正點 ] ====================
// ---------- 網路任務 (修正版) ----------
void networkTask(void* pvParameters) {
  float weightToUpload;  // 從佇列接收的仍然是精確的 float
  for (;;) {
    if (xQueueReceive(uploadQueue, &weightToUpload, portMAX_DELAY)) {
      if (WiFi.status() == WL_CONNECTED) {
        WiFiClientSecure client;
        client.setInsecure();
        HTTPClient http;

        // 1. 在這裡才將 float 四捨五入為整數 (long)
        long weightAsInt = (long)round(weightToUpload);

        // 2. 使用新的整數變數來組合 URL，並且不指定小數位數 ( String(weightAsInt) )
        String url = String(SCRIPT_URL) + "?weight=" + String(weightAsInt) + "&device=ESP32-RTOS";

        if (http.begin(client, url)) {
          int httpCode = http.GET();
          // 3. (可選) 更新序列埠監控，顯示我們發送的整數值
          Serial.printf("Upload result: %d (Sent integer: %ld)\n", httpCode, weightAsInt);
          http.end();
        }
      }
    }
  }
}
// ===================================================


// ---------- 校正程序 (與前版相同) ----------
bool runCalibration() {
  scale.set_scale(1.0f);
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Tare... Empty");
  scale.tare();
  int stableBatches = 0;
  long lastMean = LONG_MIN;
  while (stableBatches < 10) {
    long s = 0;
    for (int i = 0; i < 10; i++) {
      s += scale.get_value(1);
      delay(8);
    }
    long m = s / 10;
    if (lastMean == LONG_MIN || labs(m - lastMean) <= CAL_RAW_STABILITY_THRESHOLD) stableBatches++;
    else stableBatches = 0;
    lastMean = m;
  }
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Put 100g...");
  unsigned long t0 = millis();
  while (millis() - t0 < WAIT_PUT_TIMEOUT_MS) {
    if (labs(scale.get_value(5)) > PLACE_DETECT_THRESHOLD_RAW) break;
    delay(30);
  }
  lcd.setCursor(0, 1);
  lcd.print("Reading...      ");
  stableBatches = 0;
  lastMean = LONG_MIN;
  long raw100 = 0;
  while (stableBatches < 10) {
    long s = 0;
    for (int i = 0; i < 10; i++) {
      s += scale.get_value(1);
      delay(8);
    }
    long m = s / 10;
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
  scaleFactor = factor;
  scale.set_scale(scaleFactor);
  if (scale.get_units(10) < 0) {
    scaleFactor = -scaleFactor;
    scale.set_scale(scaleFactor);
  }
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Cal OK");
  delay(500);
  return true;
}

void resetMeasurementState() {
  stability.pos = stability.count = 0;
  stability.stableSince = 0;
  stability.isStable = stability.wasStable = false;
  gEMA = 0;
  lastShownWeight = 1e9;
}

// ---------- 按鈕處理 (與前版相同) ----------
void handleButton() {
  int lv = digitalRead(BTN_PIN);
  if (lv == LOW && !button.wasLow) {
    button.wasLow = true;
    button.downAt = millis();
  } else if (lv == HIGH && button.wasLow) {
    unsigned long dur = millis() - button.downAt;
    button.wasLow = false;
    if (dur >= Button::LONG_PRESS_MS) {
      isCalibrated = false;
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Calibrating...");
      if (runCalibration()) isCalibrated = true;
      resetMeasurementState();
      lcdFrame();
      lcdSetStatus();
    } else if (dur <= Button::SHORT_MAX_MS) {
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
  pinMode(BTN_PIN, INPUT_PULLUP);
  pinMode(WIFI_LED, OUTPUT);
  digitalWrite(WIFI_LED, LOW);
  Serial.begin(115200);
  Wire.begin(I2C_SDA, I2C_SCL);
  Wire.setClock(400000);
  lcd.init();
  lcd.backlight();
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Booting...");

  // --- WiFiManager ---
  WiFiManager wm;
  // 設定連線逾時時間(秒)，時間到會自動重啟
  wm.setConfigPortalTimeout(180);
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Config WiFi...");
  if(WiFi.status()!=WL_CONNECTED){
    lcd.setCursor(0, 1);
    lcd.print("AP: SmartScale");
  }

  if (!wm.autoConnect("SmartScale-Config")) {
    Serial.println("Failed to connect and hit timeout");
    lcd.clear();
    lcd.print("WiFi Failed");
    delay(3000);
    ESP.restart();
  }
  Serial.println("WiFi Connected!");
  lcdSetStatus();
  scale.begin(HX_DT_PIN, HX_SCK_PIN);
  scale.set_scale(1.0f);
  scale.tare();
  lcdFrame();
  // -------------------

  if (runCalibration()) isCalibrated = true;

  uploadQueue = xQueueCreate(5, sizeof(float));

  // 修正堆疊大小 (前一版已修正)
  xTaskCreatePinnedToCore(networkTask, "Network Task", 8192, NULL, 1, NULL, 0);

  unsigned long now = millis();
  tSample = tDisplay = tUploadTick = tWiFi = now;
}

// loop 迴圈完全不變
void loop() {
  unsigned long now = millis();
  handleButton();
  if (now - tWiFi >= WIFI_TICK_MS) {
    ledUpdate();
    tWiFi = now;
  }  // 不再需要 manageWiFi()
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
    } else {
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
    lcdSetStatus();
    tDisplay = now;
  }

  // 4) 上傳邏輯
  if (now - tUploadTick >= UPLOAD_TICK_MS) {
    bool becameStable = (!stability.wasStable && stability.isStable);
    bool cooldownOK = (now - uploader.lastUploadAt >= UploadManager::COOLDOWN_MS);
    bool validWeight = (fabs(lastShownWeight) >= UploadManager::MIN_VALID_G);
    bool bigChange = (fabs(lastShownWeight - uploader.lastUploadedWeight) >= UploadManager::MIN_RECORD_DELTA_G);

    if (becameStable && cooldownOK && validWeight && bigChange) {
      float weightToSend = lastShownWeight;
      if (xQueueSend(uploadQueue, &weightToSend, (TickType_t)0) == pdPASS) {
        uploader.lastUploadAt = now;
        uploader.lastUploadedWeight = weightToSend;
        lcd.setCursor(11, 1);
        lcd.print("Y*");
      }
    }
    stability.wasStable = stability.isStable;
    tUploadTick = now;
  }
}
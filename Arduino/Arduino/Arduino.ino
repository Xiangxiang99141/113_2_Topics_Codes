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
#include <Preferences.h>  // <<<<<< 新增

// [WebSocket 設定]
// ==============================================================
// 原本寫死 const char* / const int，改成可變並可保存
char WS_HOST[40] = "192.168.50.49";
int WS_PORT = 8080;
const char* WS_PATH = "";  // 伺服器上的路徑
// ==============================================================

Preferences prefs;  // <<<<<< 新增

WebSocketsClient webSocket;
const int HX_DT_PIN = 23;
const int HX_SCK_PIN = 18;
const int I2C_SDA = 16;
const int I2C_SCL = 17;
const int BTN_PIN = 14;
const int WIFI_LED = 2;

const float CAL_WEIGHT_G = 100.0f;
const unsigned long WAIT_PUT_TIMEOUT_MS = 20000;
const long PLACE_DETECT_THRESHOLD_RAW = 8000;
const long CAL_RAW_STABILITY_THRESHOLD = 100;

LiquidCrystal_I2C lcd(0x27, 16, 2);

const unsigned long SAMPLE_PERIOD_MS = 30;
const unsigned long DISPLAY_PERIOD_MS = 80;
const unsigned long UPLOAD_TICK_MS = 250;
const unsigned long WIFI_TICK_MS = 1000;
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
  constexpr static float ZERO_DETECT_THRESHOLD_G = 40.0f;
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

// ---------- 小工具 & LCD 顯示 ----------
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
  lcd.print("WiFi:? STB:?      ");
}
void lcdSetWeight(float g) {
  lcd.setCursor(8, 0);
  char buf[7];
  snprintf(buf, sizeof(buf), "%6.1f", g);
  lcd.print(buf);
}
void lcdSetStatus() {
  lcd.setCursor(5, 1);
  if (WiFi.status() != WL_CONNECTED) lcd.print(".. ");
  else lcd.print(webSocket.isConnected() ? "WS " : "OK ");
  lcd.setCursor(11, 1);
  lcd.print(stability.isStable ? "Y " : "N ");
}

// ---------- WebSocket 事件處理 ----------
void webSocketEvent(WStype_t type, uint8_t* payload, size_t length) {
  switch (type) {
    case WStype_DISCONNECTED:
      Serial.printf("[WSc] Disconnected!\n");
      break;
    case WStype_CONNECTED:
      Serial.printf("[WSc] Connected to url: %s\n", payload);
      break;
    case WStype_TEXT:
      Serial.printf("[WSc] get text: %s\n", payload);
      break;
    case WStype_BIN:
    case WStype_ERROR:
    case WStype_FRAGMENT_TEXT_START:
    case WStype_FRAGMENT_BIN_START:
    case WStype_FRAGMENT:
    case WStype_FRAGMENT_FIN:
      break;
  }
}

// ---------- 網路任務 ----------
void networkTask(void* pvParameters) {
  float weightToUpload;
  const TickType_t xQueueTimeout = pdMS_TO_TICKS(50);
  char weightString[10];

  for (;;) {
    webSocket.loop();

    if (xQueueReceive(uploadQueue, &weightToUpload, xQueueTimeout)) {
      if (webSocket.isConnected()) {

        // 1. float 轉 string
        dtostrf(weightToUpload, 4, 1, weightString);

        // 2. 組合 payload (包含 "p":"master")
        char payload[100];
        snprintf(payload, sizeof(payload),
                 "{\"p\":\"master\",\"type\":\"W\", \"data\":\"%s\"}",
                 weightString);

        // 3. 發送
        webSocket.sendTXT(payload);
        Serial.printf("WebSocket SENT: %s\n", payload);
      } else {
        Serial.println("WebSocket disconnected. Data dropped.");
      }
    }
  }
}

// ---------- 校正程序 ----------
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

    long diff = labs(m - lastMean);
    Serial.print("Current Mean: ");
    Serial.print(m);
    Serial.print(" | Diff: ");
    Serial.print(diff);
    Serial.print(" | Threshold: ");
    Serial.println(CAL_RAW_STABILITY_THRESHOLD);

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

// ================= Setup =================
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

  // --- 先讀取已保存的 WS 設定 ---
  prefs.begin("smartscale", false);
  String savedHost = prefs.getString("ws_host", "192.168.50.49");
  int savedPort = prefs.getInt("ws_port", 8080);
  strlcpy(WS_HOST, savedHost.c_str(), sizeof(WS_HOST));
  WS_PORT = savedPort;

  // --- WiFiManager ---
  WiFiManager wm;
  wm.setConfigPortalTimeout(180);
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Config WiFi...");
  lcd.setCursor(0, 1);
  lcd.print("AP: SmartScale");

  // 加入可輸入 WS Host/IP 與 Port
  WiFiManagerParameter p_ws_host("ws_host", "WS Host / IP", WS_HOST, 39);
  char portBuf[8];
  snprintf(portBuf, sizeof(portBuf), "%d", WS_PORT);
  WiFiManagerParameter p_ws_port("ws_port", "WS Port", portBuf, 7);
  wm.addParameter(&p_ws_host);
  wm.addParameter(&p_ws_port);

  if (!wm.autoConnect("SmartScale-Config")) {
    Serial.println("Failed to connect and hit timeout");
    lcd.clear();
    lcd.print("WiFi Failed");
    delay(3000);
    ESP.restart();
  }

  Serial.println("WiFi Connected!");

  // 取回使用者輸入 + 防呆 + 存入 NVS
  strlcpy(WS_HOST, p_ws_host.getValue(), sizeof(WS_HOST));
  WS_PORT = atoi(p_ws_port.getValue());

  if (strlen(WS_HOST) == 0) strlcpy(WS_HOST, "192.168.50.49", sizeof(WS_HOST));
  if (WS_PORT <= 0 || WS_PORT > 65535) WS_PORT = 8080;

  prefs.putString("ws_host", WS_HOST);
  prefs.putInt("ws_port", WS_PORT);
  prefs.end();
  Serial.printf("Using WS_HOST=%s, WS_PORT=%d\n", WS_HOST, WS_PORT);

  // --- WebSocket ---
  if (WS_PORT == 443) {
    webSocket.beginSSL(WS_HOST, WS_PORT, WS_PATH);
  } else {
    webSocket.begin(WS_HOST, WS_PORT, WS_PATH);
  }
  webSocket.onEvent(webSocketEvent);
  webSocket.setReconnectInterval(5000);
  // ===============================================

  // --- HX711 & Task ---
  scale.begin(HX_DT_PIN, HX_SCK_PIN);
  scale.set_scale(1.0f);
  scale.tare();
  if (runCalibration()) isCalibrated = true;

  uploadQueue = xQueueCreate(5, sizeof(float));
  xTaskCreatePinnedToCore(networkTask, "Network Task", 8192, NULL, 1, NULL, 0);

  lcdFrame();
  lcdSetStatus();
  unsigned long now = millis();
  tSample = tDisplay = tUploadTick = tWiFi = now;
}

// ================= Loop =================
void loop() {
  unsigned long now = millis();
  // handleButton();

  if (now - tWiFi >= WIFI_TICK_MS) {
    ledUpdate();
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

    Serial.print("gEMA:");
    Serial.println(gEMA);
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

    stability.wasStable = stability.isStable;

    if (sd_ok) {
      if (!stability.isStable) {
        if (stability.stableSince == 0) stability.stableSince = now;
        if (now - stability.stableSince >= StabilityTracker::DWELL_MS) stability.isStable = true;
      }
    } else {
      stability.isStable = false;
      stability.stableSince = 0;
    }

    // 3) 顯示（負數修正：<0 顯示 0.0）
    if (now - tDisplay >= DISPLAY_PERIOD_MS) {
      float gDisp = gEMA;
      if (gDisp < 0) gDisp = 0.0f;  // <<<<<< 負數修正

      if (fabs(gDisp - lastShownWeight) >= DISPLAY_DEADBAND_G) {
        lcdSetWeight(gDisp);
        lastShownWeight = gDisp;
      }
      lcdSetStatus();
      tDisplay = now;
    }

    // 4) 上傳節奏（負數修正：<0 上傳 0.0）
    if (now - tUploadTick >= UPLOAD_TICK_MS) {
      float gUp = gEMA;
      if (gUp <= UploadManager::ZERO_DETECT_THRESHOLD_G) gUp = 0.0f;  // <<<<<< 負數修正

      bool stableRise = (stability.isStable && !stability.wasStable);
      bool cool_ok = (now - uploader.lastUploadAt >= UploadManager::COOLDOWN_MS);
      bool delta_ok = (fabs(gUp - uploader.lastUploadedWeight) >= UploadManager::MIN_RECORD_DELTA_G);
      bool valid_ok = (gUp == 0.0f) || (gUp >= UploadManager::MIN_VALID_G);

      if (stableRise && cool_ok && delta_ok && valid_ok) {
        if (uploadQueue) {
          xQueueSend(uploadQueue, &gUp, 0);
          uploader.lastUploadAt = now;
          uploader.lastUploadedWeight = gUp;
        }
      }
      tUploadTick = now;
    }
  }
}
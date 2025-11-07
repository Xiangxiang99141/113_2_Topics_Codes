from PySide6.QtWidgets import  QMainWindow,QStatusBar,QMenuBar,QGridLayout,QLabel,QWidget,QTextEdit,QDialogButtonBox
from PySide6.QtGui import QPixmap,QFont,QAction
from PySide6.QtCore import Qt
from module.dialog import ModelErrorDialog

class InfoPayload():
    def __init__(self):
        self.area = 0
        self.coord = (500,600) #座標
        self.conf = 0.9
    def setInfo(self,area:int,coord:tuple,conf:float):
        self.area = area
        self.coord = coord
        self.conf = conf


class MainWindow(QMainWindow):
    
    def __init__(self,parent):
        super().__init__()
        self.setWindowTitle("芒果分類檢測程式")
        
        # 創建中央 widget 因為mainWindow有固定版面
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        
        menubar = self.menuBar()
        
        self.Start = QAction("啟動",self)
        
        menubar.addAction(self.Start)
        
        #創建一個水平佈局
        content_layout = QGridLayout(central_widget)
        content_layout.setSpacing(10)

        # 3️⃣ 偵測結果圖（左大圖）
        self.detect_img_label = QLabel("偵測結果圖未載入")
        self.detect_img_label.setAlignment(Qt.AlignCenter)
        self.detect_img_label.setStyleSheet("border: 2px solid #999;")
        self.detect_img_label.setMinimumSize(800, 600)  # 左邊大圖
        detect_pixmap = QPixmap("detect_result.jpg")
        if not detect_pixmap.isNull():
            self.detect_img_label.setPixmap(detect_pixmap.scaled(900, 700, Qt.AspectRatioMode.KeepAspectRatio))

        # 4️⃣ 原始圖（右上小圖）
        self.origin_img_label = QLabel("原始圖未載入")
        self.origin_img_label.setAlignment(Qt.AlignCenter)
        self.origin_img_label.setStyleSheet("border: 2px solid #aaa;")
        # 修正：應該設定 origin_img_label 的最小尺寸，而非 detect_img_label
        self.origin_img_label.setMinimumSize(300, 200)
        origin_pixmap = QPixmap("origin_image.jpg")
        if not origin_pixmap.isNull():
            self.origin_img_label.setPixmap(origin_pixmap.scaled(300, 200, Qt.AspectRatioMode.KeepAspectRatio))

        # 5️⃣ 等級顯示（右中）
        self.level_label = QLabel("等級區塊")
        self.level_label.setAlignment(Qt.AlignCenter)
        self.level_label.setFont(QFont("Microsoft JhengHei", 16, QFont.Bold))
        self.level_label.setStyleSheet("color: green; border: 1px solid #ccc; padding: 8px;")

        # 6️⃣ 偵測資訊（右下）
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setPlaceholderText("偵測資訊會顯示在此處（如座標、面積、信心值...）")
        self.info_text.setStyleSheet("background-color: #212121; border: 1px solid #fff;")

        # 7️⃣ 佈局位置
        content_layout.addWidget(self.detect_img_label, 0, 0, 3, 1)  # 偵測圖佔兩列
        content_layout.addWidget(self.origin_img_label, 0, 1)        # 原始圖（右上）
        content_layout.addWidget(self.level_label, 1, 1)             # 等級（右中）
        content_layout.addWidget(self.info_text, 2, 1)         # 資訊（底部橫跨兩欄）

        # 8️⃣ 設定比例（讓左大右小）
        content_layout.setColumnStretch(0, 3)
        content_layout.setColumnStretch(1, 1)
        content_layout.setRowStretch(0, 1)
        content_layout.setRowStretch(1, 1)
        content_layout.setRowStretch(2, 1)
        
        #創建狀態欄
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)
                # 1️⃣ 左側：主要訊息區（可變動的訊息）
        self.status_message = QLabel("就緒")
        self.status_message.setStyleSheet("padding: 2px 10px;")
        self.status_bar.addWidget(self.status_message, 1)  # stretch=1 會佔據剩餘空間
        
        # 2️⃣ 中間：模型狀態
        self.status_model = QLabel("模型：未載入")
        self.status_model.setStyleSheet("padding: 2px 10px; border-left: 1px solid #555;")
        self.status_bar.addPermanentWidget(self.status_model)
        
        # # 3️⃣ 中間：處理速度
        # self.status_fps = QLabel("⏱️ FPS: --")
        # self.status_fps.setStyleSheet("padding: 2px 10px; border-left: 1px solid #555;")
        # self.status_bar.addPermanentWidget(self.status_fps)
        
        # # 4️⃣ 右側：偵測數量
        # self.status_count = QLabel("📊 偵測數: 0")
        # self.status_count.setStyleSheet("padding: 2px 10px; border-left: 1px solid #555;")
        # self.status_bar.addPermanentWidget(self.status_count)
        
        # 5️⃣ 最右側：時間戳記
        self.status_time = QLabel("🕐 --:--:--")
        self.status_time.setStyleSheet("padding: 2px 10px; border-left: 1px solid #555;")
        self.status_bar.addPermanentWidget(self.status_time)
        self.model_load_error_dialog = ModelErrorDialog(self)
    
    #更新頁面
    def update_result(self, detect_path, origin_path, level:str, info:InfoPayload):
        detect_pixmap = QPixmap(detect_path)
        if not detect_pixmap.isNull():
            self.detect_img_label.setPixmap(detect_pixmap.scaled(900, 700, Qt.KeepAspectRatio))

        origin_pixmap = QPixmap(origin_path)
        if not origin_pixmap.isNull():
            self.origin_img_label.setPixmap(origin_pixmap.scaled(300, 200, Qt.KeepAspectRatio))

        self.level_label.setText(f"等級：{level}級")
        self.info_text.setPlainText(f"面積：{info.area} px²\n座標：{info.coord}\n信心值：{info.conf}")
        
    def updata_status(self,message:str,timeout=0):
        if timeout > 0:
            self.status_bar.showMessage(message, timeout)
        else:
            self.status_message.setText(message)
        
    def update_model_status(self, is_loaded: bool):
        """更新模型狀態"""
        if is_loaded:
            self.status_model.setText(f"🟢 模型：已載入")
            self.status_model.setStyleSheet("padding: 2px 10px; border-left: 1px solid #555; color: #00ff00;")
        else:
            self.status_model.setText("⚪ 模型：未載入")
            self.status_model.setStyleSheet("padding: 2px 10px; border-left: 1px solid #555; color: #999;")
    
    def update_timestamp(self, time_str: str):
        """更新時間戳記"""
        self.status_time.setText(f"🕐 {time_str}")
    
    def update_info_text(self,info:InfoPayload):
        self.info_text.setText(f"Conf:{info.conf}")
    
    def update_level_label(self,level:str):
        self.level_label.setText(f"等級：{level}級")
        
    def get_picture_div_size(self):
        # ori = self.origin_img_label.geometry()
        ori = self.origin_img_label.size()
        detect = self.detect_img_label.size()
        return({
            "ori":{
                "height":ori.height(),
                "width":ori.width()
            },
            "detect":{
                "height":detect.height(),
                "width":detect.width()
            }
        })
        
    def clearPixmap(self):
        self.origin_img_label.clear()
        self.origin_img_label.setText("原始圖未載入")
        self.detect_img_label.clear()
        self.detect_img_label.setText("偵測結果圖未載入")

    # def on_reload_btn_click(self):
    #     print(f"[DEBUG] {self.parent}")
    #     try:
    #         self.parent.reload_model()
    #     except Exception as e:
    #         # print(f"[ERROR] parent 沒有reload_model()")
    #         print(f"[ERROR] {e}")

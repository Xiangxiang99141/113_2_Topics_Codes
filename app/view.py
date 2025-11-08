from PySide6.QtWidgets import QApplication,QFileDialog
from views.appv4 import MainWindow, InfoPayload
from views.init_windows import SimpleSplashScreen
from PySide6.QtCore import QTimer, QThreadPool
import cv2 as cv
from module.custom import covert_to_Qpixmap
from module.websocket import WebSocket
from module.loader import ModelLoader
import os
import json
from views.setting import WebSocketConfigWindow

class App(QApplication):
    def __init__(self, argv, model_path):
        super().__init__(argv)
        
        self.model_path = model_path
        self.model = None
        self.window = None
        self.cap = None
        self.is_running = False   # <- 初始為 False，避免 None 判斷錯誤
        self.img_label_size = None
        self.cls: dict = None
        
        # 1️⃣ 立即顯示啟動畫面（極速）
        self.splash = SimpleSplashScreen()
        self.splash.show()
        self.splash.showMessage("初始化中...")
        self.processEvents()  # 強制刷新，立即顯示
        # 2️⃣ 延遲載入主視窗（讓 splash 先顯示）
        QTimer.singleShot(50, self.init_main_window)
        
        #設計多線程讀取
        self.thread_pool = QThreadPool()
        #設定定時更新畫面
        self.update_frame_timer = QTimer(self)
        self.update_frame_timer.timeout.connect(self.update_frame)
        
        
        
        # websocket 會在 background thread 啟動 server（已改成非阻塞）
        with open(f"{os.getcwd()}/config.json") as config_file:
            config = json.load(config_file)['websocket']
            self.websocket = WebSocket(config['host'], config['port'],config['recivers'])
            self.websocket.is_start.connect(self.on_websocket_start)
            self.websocket.on_connection.connect(self.on_websocket_connection)
            self.websocket.on_reciver.connect(self.on_wescoket_reciver)
    
    def init_main_window(self):
        """初始化主視窗"""
        try:
            self.splash.showMessage("正在建立主視窗...")
            # print("[DEBUG] 開始建立主視窗")
            
            # 建立主視窗
            self.window = MainWindow(self)
            self.window.model_load_error_dialog.buttons.reload_btn.clicked.connect(self.on_reload_model_btn_click)
            self.window.model_load_error_dialog.buttons.open_model_btn.clicked.connect(self.on_open_new_model_btn_click)
            # print("[DEBUG] MainWindow 創建成功")
            
            self.infoPayload = InfoPayload()
            self.infoPayload.setInfo(0, (0, 0), 0)
            # print("[DEBUG] InfoPayload 創建成功")
            
            # 背景啟動websocket
            self.websocket.start()
            
            # 開始背景載入模型
            self.load_model_async()
            
            self.splash.showMessage("啟動完成！")
        
            # 延遲 500ms 後關閉 splash 並顯示主視窗
            QTimer.singleShot(500, self.show_main_window)

        except Exception as e:
            print(f"[ERROR] 主視窗初始化失敗: {e}")
            import traceback
            traceback.print_exc()
            self.splash.showMessage(f"初始化失敗: {e}")
            QTimer.singleShot(3000, self.quit)
    
    def load_model_async(self):
        """非同步載入模型"""
        #避免重複載入
        if hasattr(self, "model_loader") and self.model_loader.isRunning():
            print("[WARN] 模型載入執行緒仍在執行，略過本次請求")
            return
        self.window.updata_status("載入模型中...",5000)
        self.model_loader = ModelLoader(self.model_path)
        self.model_loader.model_loaded.connect(self.on_model_loaded)
        self.model_loader.load_error.connect(self.on_model_error)
        self.model_loader.load_progress.connect(self.on_progress)
        self.model_loader.start()
    
    def on_progress(self, message):
        """更新進度"""
        self.splash.showMessage(message)
    
    def on_model_loaded(self, model):
        """模型載入完成"""
        print("[DEBUG] 模型載入完成")
        self.model = model
        # model.names 為 dict 或 list，視 ultralytics 版本
        try:
            self.cls = model.names
        except Exception:
            self.cls = {}
        self.window.updata_status("模型載入完成",2000)
        self.window.update_model_status(True)
        self.window.start_btn.setEnabled(True)
        QTimer.singleShot(2000, self.show_ready)
    
    def on_model_error(self, error_msg):
        """模型載入失敗"""
        print(f"[ERROR] 模型載入失敗: {error_msg}")
        
        if self.window:
            self.window.updata_status(f"模型載入失敗:{error_msg}",5000)
            self.window.update_model_status(False)
            self.window.model_load_error_dialog.show()

    def on_reload_model_btn_click(self):
        print("[DEBUG] 模型重新載入中")
        self.window.updata_status("重新載入模型中...",5000)
        self.model_loader.start()

    def on_open_new_model_btn_click(self):
        self.window.model_load_error_dialog.close()
        file_dialog = QFileDialog(self.window,defaultSuffix="*.pt",filter="*.pt")
        file_dialog.fileSelected.connect(self.on_new_model_selected)
        file_dialog.show()
    def on_new_model_selected(self,path):
        print(f"[DEBUG] New Model_path:{path}")
        self.window.updata_status(f"載入模型:{path}",3000)
        self.model_loader.set_model_path(path)
        self.model_loader.start()
    
    def on_websocket_start(self,is_start:bool):
        self.window.update_websocket_status(is_start)
        msg = ""
        if is_start:
            msg = f"Server is start on ws://{self.websocket.getServerIP()}"
        else:
            msg = "Server is close"
        self.window.websocket_logs_window.add_log(msg)
    
    def on_websocket_start_stop_btn_click(self):
        if self.websocket.is_running:
            print("[WebSocket] 關閉中...")
            self.websocket.stop()
            self.websocket.wait_stop()
            self.window.websocket_start_stop_btn.setText("啟動")
        else:
            print("[WebSocket] 啟動中...")
            self.websocket.start()
            self.window.websocket_start_stop_btn.setText("關閉")
    def on_websocket_restart_btn_click(self):
        print("[WebSocket] 重新啟動中")
        self.window.websocket_restart_btn.setDisabled(True)
        if self.websocket.is_running:
            print("[WebSocket] 關閉中...")
            self.websocket.stop()
            self.websocket.wait_stop()
            print("[WebSocket] 啟動中...")
            self.websocket.start()
        else:
            print("[WebSocket] 啟動中...")
            self.websocket.start()
        self.window.websocket_restart_btn.setDisabled(False)
    def on_websocket_show_log_btn_click(self):
        self.window.websocket_logs_window.show()
        # print("[WebSocket] 顯示log")
    def on_websocket_show_setting_btn_click(self):
        setting_window = WebSocketConfigWindow(self.window)
        setting_window.config_applied.connect(self.on_websocket_setting_change)
        setting_window.config_saved.connect(self.on_websocket_setting_change)
        setting_window.exec()
    def on_websocket_setting_change(self,config):
        if self.websocket.is_running:
            self.websocket.stop()
            self.websocket.wait_stop()
        self.websocket.setting(config)
        self.websocket.start()
    def on_websocket_connection(self,data:dict):
        self.window.websocket_logs_window.add_log(f"{data['IP']} is Connection")
    def on_wescoket_reciver(self,data:dict):
        self.window.websocket_logs_window.add_log(f"Message from {data['IP']} : {data['message']}")
    
    def show_main_window(self):
        """顯示主視窗"""
        # print("[DEBUG] 準備顯示主視窗")
        
        if self.window:
            # print("[DEBUG] 視窗存在，開始顯示")
            try:
                self.window.showMaximized()
                
                #連結啟動按鈕
                self.window.start_btn.triggered.connect(self.on_start_btn_click)
                self.window.websocket_start_stop_btn.triggered.connect(self.on_websocket_start_stop_btn_click)
                self.window.websocket_restart_btn.triggered.connect(self.on_websocket_restart_btn_click)
                self.window.websocket_show_log_btn.triggered.connect(self.on_websocket_show_log_btn_click)
                self.window.websocket_show_setting_btn.triggered.connect(self.on_websocket_show_setting_btn_click)
                
                # 確保主視窗在最上層
                self.window.raise_()
                self.window.activateWindow()
                # print("[DEBUG] 主視窗已啟動")
                
            except Exception as e:
                print(f"[ERROR] 顯示主視窗時出錯: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("[ERROR] windows未初始化 是 None!")
        
        # 關閉啟動畫面
        try:
            self.splash.finish(self.window)
            # print("[DEBUG] Splash Screen 已關閉")
        except Exception as e:
            print(f"[ERROR] 關閉 Splash 時出錯: {e}")
    
    def update_initial_data(self):
        """更新初始資料"""
        self.window.update_result(
            "detect_result.jpg",
            "origin_image.jpg",
            "A",
            self.infoPayload
        )

    def show_ready(self):
        self.window.updata_status("Ready")

    def on_start_btn_click(self):
        if not self.is_running:
            self.start_camera()
            self.window.updata_status("websocket啟動成功",2000)
        else:
            self.stop_camera()
            self.websocket.stop()
            
    def start_camera(self):
        self.window.updata_status("鏡頭開啟",1000)
        self.is_running = True
        self.cap = cv.VideoCapture(0)  # Open the default camera (0)
        if not self.cap.isOpened():
            print("[ERROR] 無法開啟相機")
            self.window.updata_status("無法開啟相機",2000)
            self.is_running = False
            return
        self.window.Start.setText("關閉")
        self.img_label_size = self.window.get_picture_div_size()
        self.update_frame_timer.start(100) #1000/100=10fps

    def stop_camera(self):
        self.window.updata_status("鏡頭關閉",1000)
        self.is_running = False
        if self.cap:
            try:
                self.cap.release()  # Release the camera
            except Exception as e:
                print(f"[ERROR] release cap: {e}")
        self.cap = None
        self.window.clearPixmap()
        self.window.Start.setText("啟動")

    def update_frame(self):
        if self.is_running and self.cap:
            ret, frame = self.cap.read()
            if ret:
                self.rgb_image = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
                # 防護：若 gui 尚未取得尺寸，先更新一次
                if not self.img_label_size:
                    self.img_label_size = self.window.get_picture_div_size()
                canvas = covert_to_Qpixmap(self.rgb_image, self.img_label_size["ori"])
                self.window.origin_img_label.setPixmap(canvas)
                self.display_detect_img()
            else:
                print("Failed to capture frame")
            
    def display_detect_img(self):
        # 防護：若模型尚未載入就呼叫 predict 會 crash
        if not self.model:
            return

        try:
            # 若是分類模型， predict 回傳 list
            result = self.model.predict(self.rgb_image, device=0, verbose=False)
            info = None
            # 確保 result 有內容
            if len(result) > 0:
                r0 = result[0]
                # 若為 classification，嘗試從 r0.probs 取得資訊；若沒有則跳過
                info = getattr(r0, "probs", None)
            if info:
                # 透過 top1/top1conf 等屬性取得分類結果（不同 ultralytics 版本可能不同）
                top_idx = getattr(info, "top1", None)
                top_conf = getattr(info, "top1conf", None)
                if top_idx is not None:
                    try:
                        top_label = self.cls[top_idx] if self.cls and top_idx in self.cls else str(top_idx)
                    except Exception:
                        top_label = str(top_idx)
                    infoPayload = InfoPayload()
                    infoPayload.setInfo(0, (0,0), round(float(top_conf) if top_conf is not None else 0.0, 2))
                    self.window.update_level_label(top_label)
                    self.window.update_info_text(infoPayload)

            detectImg = result[0].plot()
            # debug
            # try:
            #     print(f"[DEBUG] detectImg shape: {detectImg.shape}")
            #     print(f"[DEBUG] detectImg dtype: {detectImg.dtype}")
            # except Exception as e:
            #     pass

            canvas = covert_to_Qpixmap(detectImg, self.img_label_size["detect"])
            self.window.detect_img_label.setPixmap(canvas)
        except Exception as e:
            print(f"[ERROR] display_detect_img: {e}")
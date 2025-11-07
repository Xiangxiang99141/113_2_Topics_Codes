from PySide6.QtCore import QThread, Signal
from ultralytics import YOLO
import os

class ModelLoader(QThread):
    """背景載入模型的執行緒"""
    model_loaded = Signal(object)  # 載入完成，傳遞 model 物件
    load_error = Signal(str)  # 載入失敗，傳遞錯誤訊息
    load_progress = Signal(str)  # 進度更新
    
    def __init__(self, model_path):
        super().__init__()
        self.model_path = model_path
    def run(self):
        self.load_progress.emit("正在載入 YOLO 模型...")
        if not os.path.exists(self.model_path):
            self.load_error.emit(f'檔案不存在')
            self.quit()
            return
        try:
            model = YOLO(self.model_path)
            self.load_progress.emit("模型載入完成")
            self.model_loaded.emit(model)
        except Exception as e:
            self.load_error.emit(f'模型載入失敗: {str(e)}')
    
    # def stop(self):
    #     self.quit()
    #     return
    
    def set_model_path(self,path):
        self.model_path = path
    
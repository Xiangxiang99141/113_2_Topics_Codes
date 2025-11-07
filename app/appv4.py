# appv4.py
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
import sys
from pathlib import Path 
from view import App

cwd_path = Path().cwd()
if __name__ == '__main__':
    # 設定高 DPI 支援（可選，讓畫面更清晰）
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    # model_path = cwd_path / 'model/model.pt'
    model_path = 'model/model.pt'
    app = App(sys.argv, model_path)
    sys.exit(app.exec())

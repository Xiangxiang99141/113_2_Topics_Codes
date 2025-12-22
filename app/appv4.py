# appv4.py
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
import sys
from pathlib import Path
from view import App
import json
import os
# cwd_path = Path().cwd()


def get_base_path():
    if getattr(sys, 'frozen', False):
        # 如果是打包後的 exe，路徑是 exe 所在的資料夾
        return os.path.dirname(sys.executable)
    else:
        # 如果是開發中的 .py，路徑是檔案所在的資料夾
        return os.path.dirname(os.path.abspath(__file__))


if __name__ == '__main__':
    base_path  = get_base_path()
    
    # 設定高 DPI 支援（可選，讓畫面更清晰）
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    #組合 config.json 的絕對路徑
    config_file_path = os.path.join(base_path, 'config.json')
    
    try:
        with open(config_file_path, 'r', encoding='utf-8') as c:
            config_data = json.load(c)
            # 假設 json 裡是寫 "path": "model/best.pt" (相對路徑)
            relative_model_path = config_data['model']['path']
    except FileNotFoundError:
        print(f"錯誤：找不到設定檔 {config_file_path}")
        sys.exit(1)
    full_model_path = os.path.join(base_path, relative_model_path)
    app = App(sys.argv, full_model_path,base_path)
    try:
        sys.exit(app.exec())
    finally:
        print("[App] 正在關閉 WebSocket...")
        app.websocket.stop()
        app.websocket.wait_stop()
        # print("[App] WebSocket 已安全關閉。")

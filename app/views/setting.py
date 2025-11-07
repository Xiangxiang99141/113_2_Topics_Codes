from PySide6.QtWidgets import (
    QDialog, QLabel, QLineEdit, QPushButton, QGridLayout, QHBoxLayout, QVBoxLayout, QMessageBox
)
from PySide6.QtCore import Qt, Signal
import os
import json

class WebSocketConfigWindow(QDialog):
    # 發射信號：套用與儲存設定
    config_applied = Signal(dict)
    config_saved = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("WebSocket 設定")
        self.setFixedSize(400, 250)
        self.setWindowModality(Qt.ApplicationModal)

        # 預設設定
        with open(f"{os.getcwd()}/config.json") as config_file:
            self.config = json.load(config_file)["websocket"]
        # self.config = default_config or {
        #     "server_ip": "127.0.0.1",
        #     "server_port": "8080",
        #     "receiver_ip": "127.0.0.1"
        # }

        # 建立元件
        self.server_ip_label = QLabel("Server IP:")
        self.server_ip_input = QLineEdit(self.config["host"])

        self.server_port_label = QLabel("Server Port:")
        self.server_port_input = QLineEdit(self.config["port"])

        self.receiver_ip_label = QLabel("Receiver IP:")
        self.receiver_ip_input = QLineEdit(",".join(self.config["recivers"]))

        # 按鈕區
        self.apply_btn = QPushButton("套用")
        self.save_btn = QPushButton("儲存")
        self.cancel_btn = QPushButton("取消")

        # 佈局
        grid = QGridLayout()
        grid.addWidget(self.server_ip_label, 0, 0)
        grid.addWidget(self.server_ip_input, 0, 1)
        grid.addWidget(self.server_port_label, 1, 0)
        grid.addWidget(self.server_port_input, 1, 1)
        grid.addWidget(self.receiver_ip_label, 2, 0)
        grid.addWidget(self.receiver_ip_input, 2, 1)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.apply_btn)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)

        main_layout = QVBoxLayout()
        main_layout.addLayout(grid)
        main_layout.addStretch()
        main_layout.addLayout(btn_layout)

        self.setLayout(main_layout)

        # 綁定事件
        self.apply_btn.clicked.connect(self.on_apply)
        self.save_btn.clicked.connect(self.on_save)
        self.cancel_btn.clicked.connect(self.reject)

    # --- 功能區 ---
    def get_config(self):
        """回傳目前設定"""
        # return {
        #     "server_ip": self.server_ip_input.text().strip(),
        #     "server_port": self.server_port_input.text().strip(),
        #     "receiver_ip": self.receiver_ip_input.text().strip()
        # }
        self.save_config()
        return self.config

    def save_config(self):
        self.config['host'] = self.server_ip_input.text().strip()
        self.config['port'] = self.server_port_input.text().strip()
        self.config['recivers'] = self.receiver_ip_input.text().strip().split(',')
        # websocket_config = json.dumps({'host': self.config['host'], 
        #                                 'port': self.config['port'],
        #                                 'recivers':self.config['recivers']}, indent=4)
        with open(f"{os.getcwd()}/config.json",'r',encoding='utf-8') as config_file:
            all_config = json.load(config_file)
        all_config['websocket'] = self.config
        with open(f"{os.getcwd()}/config.json",'w') as config_file:
            config_file.write(json.dumps(all_config,indent=4))



    def on_apply(self):
        config = self.get_config()
        self.config_applied.emit(config)
        QMessageBox.information(self, "設定", "設定已套用")

    def on_save(self):
        config = self.get_config()
        self.config_saved.emit(config)
        QMessageBox.information(self, "設定", "設定已儲存")
        self.accept()

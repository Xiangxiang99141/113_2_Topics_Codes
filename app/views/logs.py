from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QPlainTextEdit, QScrollBar
)
from PySide6.QtGui import QTextCursor, QTextCharFormat, QColor
from PySide6.QtCore import Qt, Signal, Slot
import module.date_custum as datetime

class WebSocketLogWindow(QDialog):
    """WebSocket Log 顯示視窗"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("WebSocket Log")
        self.resize(700, 500)
        # self.setWindowFlag(Qt.WindowType.)

        # --- UI 元件 ---
        self.search_label = QLabel("搜尋：")
        self.search_input = QLineEdit()
        self.search_btn = QPushButton("搜尋")
        self.clear_btn = QPushButton("清除")

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet("font-family: Consolas; font-size: 12px;")

        # --- 佈局 ---
        top_layout = QHBoxLayout()
        top_layout.addWidget(self.search_label)
        top_layout.addWidget(self.search_input)
        top_layout.addWidget(self.search_btn)
        top_layout.addWidget(self.clear_btn)

        layout = QVBoxLayout()
        layout.addLayout(top_layout)
        layout.addWidget(self.log_view)
        self.setLayout(layout)

        # --- 綁定事件 ---
        self.search_btn.clicked.connect(self.search_text)
        self.clear_btn.clicked.connect(self.clear_logs)
        self.search_input.returnPressed.connect(self.search_text)

        # --- 狀態 ---
        self.last_search = ""
        self.highlight_bg_color = QColor("#fffa65")
        self.highlight_fg_color = QColor("#000000")

    # -------------------------
    # 功能函式
    # -------------------------
    @Slot(str)
    def add_log(self, message: str):
        """新增一條 log 到視窗"""
        self.log_view.appendPlainText(f"{datetime.getDateTimeNow()}\t[WebSocket]{message}")
        # 自動滾動到底
        scrollbar: QScrollBar = self.log_view.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    @Slot()
    def clear_logs(self):
        """清除所有 log"""
        self.log_view.clear()

    @Slot()
    def search_text(self):
        """搜尋文字並高亮顯示"""
        self.search_input.setText()
        keyword = self.search_input.text().strip()
        if not keyword:
            return
        
        text = self.log_view.toPlainText()

        cursor = self.log_view.textCursor()
        format_default = QTextCharFormat()
        format_highlight = QTextCharFormat()
        format_highlight.setBackground(self.highlight_bg_color)
        format_highlight.setForeground(self.highlight_fg_color)
        # 清除舊 highlight
        cursor.beginEditBlock()
        cursor.movePosition(QTextCursor.Start)
        cursor.setPosition(0)
        cursor.select(QTextCursor.Document)
        cursor.setCharFormat(format_default)
        cursor.endEditBlock()

        # 找尋關鍵字
        if keyword:
            cursor.beginEditBlock()
            start_pos = 0
            while True:
                start_pos = text.find(keyword, start_pos)
                if start_pos == -1:
                    break
                cursor.setPosition(start_pos)
                cursor.movePosition(QTextCursor.NextCharacter, QTextCursor.KeepAnchor, len(keyword))
                cursor.setCharFormat(format_highlight)
                start_pos += len(keyword)
            cursor.endEditBlock()

        self.last_search = keyword


# --- 測試執行 ---
# if __name__ == "__main__":
#     from PySide6.QtWidgets import QApplication
#     import sys

#     app = QApplication(sys.argv)
#     w = WebSocketLogWindow()
#     w.show()

#     # 模擬 log
#     w.add_log("[WebSocket] Connected IP: 192.168.0.101")
#     w.add_log("[WebSocket] Message from 192.168.0.101: {'type':'W','data':50}")
#     w.add_log("[WebSocket] Message from 192.168.0.105: {'type':'G','data':'A'}")
#     w.add_log("[WebSocket] Disconnected: 192.168.0.101")

#     sys.exit(app.exec())

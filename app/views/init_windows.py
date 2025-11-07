from PySide6.QtWidgets import QApplication, QSplashScreen, QLabel
from PySide6.QtGui import QPixmap,QColor,QPainter,QFont
from PySide6.QtCore import Qt

class SimpleSplashScreen(QSplashScreen):
    """輕量級啟動畫面"""
    def __init__(self):
        # 創建簡單的啟動畫面（不需要圖片檔案）
        pixmap = QPixmap(600, 400)
        pixmap.fill(QColor(45, 45, 48))  # 深灰色背景
        
        super().__init__(pixmap)
        self.setWindowFlag(Qt.WindowStaysOnTopHint)
        
        # 繪製文字
        painter = QPainter(pixmap)
        painter.setPen(QColor(255, 255, 255))
        
        # 標題
        title_font = QFont("Arial", 32, QFont.Bold)
        painter.setFont(title_font)
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "芒果分類系統")
        
        # 副標題
        subtitle_font = QFont("Arial", 14)
        painter.setFont(subtitle_font)
        painter.drawText(50, 250, "正在初始化應用程式...")
        
        painter.end()
        self.setPixmap(pixmap)
        
        # 訊息標籤
        self.message_label = QLabel(self)
        self.message_label.setStyleSheet("""
            QLabel {
                color: #00FF00;
                font-size: 12px;
                background: transparent;
            }
        """)
        self.message_label.setGeometry(50, 300, 500, 30)
    
    def showMessage(self, message):
        """更新訊息"""
        self.message_label.setText(f"{message}")
        QApplication.processEvents()
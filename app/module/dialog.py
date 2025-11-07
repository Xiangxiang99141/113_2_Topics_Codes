from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel
from module.buttonbox import ModelErrorButtonBox
from PySide6.QtCore import Qt
class ModelErrorDialog(QDialog):
    def __init__(self,parent):
        super().__init__()
        self.parent = parent
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle("模型載入失敗")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("要重新載入嗎?"))
        self.buttons = ModelErrorButtonBox(self)
        layout.addWidget(self.buttons)
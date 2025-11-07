from PySide6.QtWidgets import QDialogButtonBox,QPushButton
from PySide6.QtCore import Signal


class ModelErrorButtonBox(QDialogButtonBox):
    def __init__(self,parent):
        super().__init__()
        self.parent = parent
        self.open_model_btn = QPushButton("開啟model")
        self.reload_btn = QPushButton("重新載入")
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.on_cancel_btn_click)
        self.addButton(self.open_model_btn,QDialogButtonBox.ButtonRole.AcceptRole)
        self.addButton(self.reload_btn,QDialogButtonBox.ButtonRole.ActionRole)
        self.addButton(self.cancel_btn,QDialogButtonBox.ButtonRole.RejectRole)
    
    def on_cancel_btn_click(self):
        self.parent.close()
    
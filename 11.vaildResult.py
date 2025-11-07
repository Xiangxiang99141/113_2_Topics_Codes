from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton,
    QLineEdit, QFileDialog, QMessageBox, QHBoxLayout
)
import os
import sys
import pandas as pd
from pathlib import Path


def calculate_accuracy(image_folder, label_folder):
    """
    讀取 labels/*.txt（格式: class-name conf，且由大到小排序）
    以第一行 (top-1) 的 class-name 當作預測，計算每個資料夾(類別)的準確度。
    回傳一個可直接顯示在 QLabel 的文字結果。
    """
    class_results = {}  # { class_name: (total, matched) }
    # class_results = pd.DataFrame(columns=['grade','id'])

    # 走訪每個類別資料夾 (例如 A, B, C)
    for class_name in os.listdir(image_folder):
        class_path = os.path.join(image_folder, class_name)
        if not os.path.isdir(class_path):
            continue

        images = [f for f in os.listdir(class_path) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
        total = len(images)
        matched = 0

        for img_name in images:
            stem = Path(img_name).stem
            label_file = Path(label_folder)  / f"{stem}.txt"
            # print(label_file)
            if not os.path.exists(label_file):
                # 沒有檢測檔視為未匹配（可依需求改為不計入）
                print("找不到檔案")
                continue

            # 讀取 label，取第一行 (top-1)
            with open(label_file, "r", encoding="utf-8") as f:
                # 取第一個非空行
                first_line = None
                first_line = f.readline()

            if not first_line:
                continue

            parts = first_line.split()
            pred_class = parts[1].strip()  # 格式: "conf class-name "，因此第一欄是 class-name
            # print(f"predClass:{pred_class}")
            # 比對時採用不分大小寫比對以提高魯棒性
            if pred_class.lower() == str(class_name).lower():
                matched += 1

        class_results[class_name] = (total, matched)
        # print(class_results)

    # 組合輸出文字
    result_lines = []
    total_imgs = 0
    total_matched = 0
    for cls in sorted(class_results.keys()):
        total, matched = class_results[cls]
        acc = (matched / total * 100) if total > 0 else 0.0
        result_lines.append(f"{cls}: {acc:.2f}% ({matched}/{total})")
        total_imgs += total
        total_matched += matched

    overall_acc = (total_matched / total_imgs * 100) if total_imgs > 0 else 0.0
    result_lines.append("")
    result_lines.append(f"總體準確度: {overall_acc:.2f}%")

    return "\n".join(result_lines)



class YOLOAccuracyApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YOLO 檢測準確度計算工具")
        self.setGeometry(300, 200, 600, 350)

        layout = QVBoxLayout()
        self.setLayout(layout)

        # === 原始圖片資料夾 ===
        layout.addWidget(QLabel("原始圖片資料夾路徑："))
        img_layout = QHBoxLayout()
        self.image_path = QLineEdit()
        self.image_btn = QPushButton("選擇資料夾")
        self.image_btn.clicked.connect(self.select_image_folder)
        img_layout.addWidget(self.image_path)
        img_layout.addWidget(self.image_btn)
        layout.addLayout(img_layout)

        # === YOLO labels 資料夾 ===
        layout.addWidget(QLabel("YOLO 檢測結果 (labels) 資料夾："))
        label_layout = QHBoxLayout()
        self.label_path = QLineEdit()
        self.label_btn = QPushButton("選擇資料夾")
        self.label_btn.clicked.connect(self.select_label_folder)
        label_layout.addWidget(self.label_path)
        label_layout.addWidget(self.label_btn)
        layout.addLayout(label_layout)

        # === 執行按鈕 ===
        self.run_btn = QPushButton("開始計算準確度")
        self.run_btn.setStyleSheet("background-color: #0078D7; color: white; font-weight: bold; padding: 6px;")
        self.run_btn.clicked.connect(self.run_calculation)
        layout.addWidget(self.run_btn)

        # === 結果標籤 ===
        self.result_label = QLabel("尚未計算")
        self.result_label.setStyleSheet("font-size: 16px; color: gray; margin-top: 10px;")
        layout.addWidget(self.result_label)

    def select_image_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "選擇原始圖片資料夾")
        if folder:
            self.image_path.setText(folder)

    def select_label_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "選擇 YOLO labels 資料夾")
        if folder:
            self.label_path.setText(folder)

    def run_calculation(self):
        image_folder = self.image_path.text().strip()
        label_folder = self.label_path.text().strip()

        if not os.path.exists(image_folder):
            QMessageBox.critical(self, "錯誤", f"圖片資料夾不存在：\n{image_folder}")
            return
        if not os.path.exists(label_folder):
            QMessageBox.critical(self, "錯誤", f"labels 資料夾不存在：\n{label_folder}")
            return

        result_text = calculate_accuracy(image_folder, label_folder)
        self.result_label.setText(result_text)
        self.result_label.setStyleSheet("font-size: 14px; color: white; font-family: Consolas;")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = YOLOAccuracyApp()
    window.show()
    sys.exit(app.exec())

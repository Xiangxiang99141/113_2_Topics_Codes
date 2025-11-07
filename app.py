import tkinter as tk
from tkinter import filedialog, ttk,messagebox
from tkinter.ttk import Label,Button,Combobox,Spinbox
import cv2
from PIL import Image, ImageTk
from ultralytics import YOLO


class YOLOApp:
    def __init__(self, window:tk.Tk):
        self.window = window
        self.window.title("YOLO 檢測系統")
        self.window.state("zoomed")  # 最大化視窗
        print(self.window.winfo_width(),self.window.winfo_height())
        
        # 模式選單區塊
        control_frame = tk.Frame(window)
        control_frame.pack(pady=10)

        self.mode = tk.StringVar(value="camera")
        self.dropdown = Combobox(control_frame, textvariable=self.mode, values=["camera", "image"], state="readonly", width=10)
        self.dropdown.grid(row=0, column=0, padx=5)
        self.camId = tk.IntVar(value=0)  # 預設攝影機ID為0
        self.camSpinbox = Spinbox(control_frame,from_=0,to=10,textvariable=self.camId)
        self.camSpinbox.grid(row=0, column=1, padx=5)
        
        
        self.start_btn = Button(control_frame, text="啟動", command=self.start_detection)
        self.start_btn.grid(row=0, column=2, padx=5)

        self.stop_btn = Button(control_frame, text="停止", command=self.stop_camera)
        self.stop_btn.grid(row=0, column=3, padx=5)
        self.stop_btn.config(state="disabled")  # 預設關閉

        # 顯示畫面區域
        self.display_frame = tk.Frame(window, width=640, height=480)
        self.display_frame.pack(pady=10)
        self.display_frame.pack_propagate(False)  # 防止 frame 自動調整大小
        
        self.lvLabel = Label(self.display_frame)
        self.lvLabel.pack(fill=tk.BOTH, expand=True)

        self.model = None
        #載入model
        self.load_model(r'.\model\mango_detect_seg_v1.pt')
        self.cap = None
        self.running = False
        
        # 設定默認的顯示大小
        self.display_width = 640
        self.display_height = 480

    def load_model(self,model_path):
        if self.model is None:
            print("載入 YOLO 模型中...")
            self.model = YOLO(model_path)
            print("模型載入完成！")

    def start_detection(self):
        selected_mode = self.mode.get()

        # 獲取當前顯示區域的大小
        self.display_width = self.display_frame.winfo_width()
        self.display_height = self.display_frame.winfo_height()

        if selected_mode == "camera":
            self.start_camera_mode(int(self.camSpinbox.get()))
        elif selected_mode == "image":
            self.select_and_process_image()
            # 圖片模式完成後立即重新啟用控制元件
            self.dropdown.config(state="readonly")
            self.start_btn.config(state="normal")
            self.stop_btn.config(state="disabled")

    def start_camera_mode(self,cam_id):
        self.cap = cv2.VideoCapture(cam_id)
        if not self.cap.isOpened():
            messagebox.showerror("錯誤", f"無法打開攝影機 {cam_id}，請檢查攝影機連接。")
            return
        self.running = True
        
        # 禁用控制元件
        self.dropdown.config(state="disabled")
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.update_camera_frame()

    def update_camera_frame(self):
        if not self.running:
            return
        ret, frame = self.cap.read()
        if ret:
            results = self.model(frame, verbose=False,conf=0.5)  # 設定信心度閾值
            annotated = results[0].plot()
            rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb)
            
            # 調整圖片大小以適應顯示區域
            img = self.resize_image(img, self.display_width, self.display_height)
            
            imgtk = ImageTk.PhotoImage(image=img)
            self.lvLabel.imgtk = imgtk
            self.lvLabel.configure(image=imgtk)
        self.window.after(10, self.update_camera_frame)

    def select_and_process_image(self):
        filepath = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png")])
        if filepath:
            image = cv2.imread(filepath)
            results = self.model(image, verbose=False)
            annotated = results[0].plot()
            rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb)
            img = self.resize_image(img, self.display_width, self.display_height)
            imgtk = ImageTk.PhotoImage(image=img)
            self.lvLabel.imgtk = imgtk
            self.lvLabel.configure(image=imgtk)

    def resize_image(self, img, width, height):
        """調整圖片大小以適應顯示區域"""
        # 獲取圖片原始大小
        img_width, img_height = img.size
        
        # 計算縮放比例
        width_ratio = width / img_width
        height_ratio = height / img_height
        ratio = min(width_ratio, height_ratio)  # 取較小值保持圖片比例
        
        # 計算新的尺寸
        new_width = int(img_width * ratio)
        new_height = int(img_height * ratio)
        
        # 調整圖片大小
        return img.resize((new_width, new_height), Image.LANCZOS)

    def stop_camera(self):
        self.running = False
        if self.cap:
            self.cap.release()
            self.cap = None
        self.lvLabel.config(image="")  # 清除畫面
        self.dropdown.config(state="readonly")
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")

    def on_closing(self):
        print("關閉視窗，釋放資源中...")
        self.running = False
        self.stop_camera()
        self.window.destroy() 


if __name__ == "__main__":
    root = tk.Tk()
    app = YOLOApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

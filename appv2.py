import tkinter as tk
from tkinter import ttk,messagebox
from PIL import Image, ImageTk
from ultralytics import YOLO
import cv2
from backgroundremover.bg import remove
import numpy as np
from io import BytesIO


class YOLOApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("YOLO影像辨識")
        self.state("zoomed")
        # self.configure(bg="white")
        self.target_width = 320
        self.target_height = 240
        self.mango_area = tk.IntVar()
        self.mango_area.set(0)
        self.mango_black_area = tk.IntVar()
        self.mango_black_area.set(0)
        img = Image.open(r"test\init_picture.jpg")
        self.default_tk_image = ImageTk.PhotoImage(img)
        self.create_widgets()
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)  # 設定關閉視窗的事件處理器
        
        
        self.model = None
        #載入model
        self.load_model(r'.\model\mango_detect.pt')
        self.cap = None
        self.is_camera_running = False


    def create_widgets(self):

        left = ttk.Frame(self, width=100,padding=10)
        left.grid(row=0, column=0)

        button_frame = ttk.Frame(left, width=100,height=100,padding=10)
        button_frame.pack()
        self.camera_btn = ttk.Button(button_frame, text="啟動",padding=30,command=self.toggle_camera)
        self.camera_btn.pack()

        # 操作 & 分析（左中）
        control_frame = ttk.Frame(left, width=100,height=100,padding=10)
        control_frame.pack()
        #芒果座標
        position_frame = ttk.Labelframe(left, width=100,height=100,padding=10,text="座標")
        position_frame.pack()
        self.position_label = ttk.Label(position_frame, text="x:\ny:")
        self.position_label.pack()
        # 黑點比對文字（左下）
        black_frame = ttk.Labelframe(left, width=100,height=100,padding=10,text="黑點分析")
        black_frame.pack()
        area_label = ttk.Label(black_frame, text=f"面積：{self.mango_area.get()}")
        area_label.pack()
        black_area_label = ttk.Label(black_frame, text= f"黑點{self.mango_black_area.get()}")
        black_area_label.pack()
        black_and_area_label = ttk.Label(black_frame,
        text= f"比例{(self.mango_black_area.get()/self.mango_area.get()) if self.mango_area.get()>0 else 0}"
        )
        black_and_area_label.pack()

        right = ttk.Frame(self, width=100, padding=10)
        right.grid(row=0, column=1)

        mango_origin_frame = ttk.Frame(right, width=self.target_width,height=self.target_height+30,padding=10)
        mango_origin_frame.grid(row=0, column=0)
        mango_origin_label = ttk.Label(mango_origin_frame, text="原始圖片")
        mango_origin_label.pack()
        self.mango_origin_img = ttk.Label(mango_origin_frame,image=self.default_tk_image)
        self.mango_origin_img.pack()

        mango_rembg_frame = ttk.Frame(right, width=self.target_width,height=self.target_height+30,padding=10)
        mango_rembg_frame.grid(row=0, column=1)
        mango_rembg_label = ttk.Label(mango_rembg_frame, text="去背圖片")
        mango_rembg_label.pack()
        self.mango_rembg_img = ttk.Label(mango_rembg_frame,image=self.default_tk_image)
        self.mango_rembg_img.pack()

        mango_gray_frame = ttk.Frame(right, width=self.target_width,height=self.target_height+30,padding=10)
        mango_gray_frame.grid(row=1, column=0)
        mango_gray_label = ttk.Label(mango_gray_frame, text="灰階圖片")
        mango_gray_label.pack()
        self.mango_gray_img = ttk.Label(mango_gray_frame,image=self.default_tk_image)
        self.mango_gray_img.pack()

        mango_black_frame = ttk.Frame(right, width=self.target_width,height=self.target_height+30,padding=10)
        mango_black_frame.grid(row=1, column=1)
        mango_black_label = ttk.Label(mango_black_frame, text="黑點圖片")
        mango_black_label.pack()
        self.mango_black_img = ttk.Label(mango_black_frame,image=self.default_tk_image)
        self.mango_black_img.pack()

    def load_model(self,model_path):
        if self.model is None:
            print("載入 YOLO 模型中...")
            self.model = YOLO(model_path)
            print("模型載入完成！")

    def toggle_camera(self):
        """切換攝影機開啟/關閉狀態"""
        if self.is_camera_running:
            self.stop_camera()
            self.camera_btn.configure(text="啟動視訊")
        else:
            self.start_camera()
            self.camera_btn.configure(text="停止視訊")
    
    def start_camera(self):
        """啟動攝影機"""
        if not self.is_camera_running:
            # 嘗試開啟預設攝影機
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                messagebox.showerror("錯誤", "無法開啟攝影機")
                return
            
            self.is_camera_running = True
            self.update_frame()
    
    def stop_camera(self):
        """停止攝影機"""
        if self.is_camera_running:
            self.is_camera_running = False
            if self.cap is not None:
                self.cap.release()
                self.cap = None
            
            # 清空顯示
            self.origin_img = self.default_tk_image
            self.rembg_img=self.default_tk_image         
            self.gray_img=self.default_tk_image
            self.black_img=self.default_tk_image

    def update_frame(self):
        """更新攝影機畫面"""
        if self.is_camera_running:
            ret, frame = self.cap.read()
            cv2.cvtColor(frame, cv2.COLOR_BGR2RGB,dst=frame)
            #是否有正確讀取到攝影機
            if not ret:
                self.stop_camera()
                messagebox.showerror("錯誤", "無法讀取攝影機畫面")
                return
            
            # 取得預測結果
            result = self.model.predict(
                frame, 
                conf=0.5,
                verbose=False, #不在console 顯示訊息 
                imgsz=320,
                # show=True, 
                # save=True, 
                # save_txt=True, 
                # project="source", 
                # name="A"
            )[0]
            img = result.plot()
            cv2.resize(img, (self.target_width, self.target_height), dst=img) #調整影像大小
            pil_img = Image.fromarray(img if result.boxes!= None else frame) #如果沒有偵測到物件就顯示原始影像
            print(pil_img.size)
            self.display_origin_image(pil_img)
            if(result.boxes==None):
                self.display_rembg_image(pil_img)
                self.position_label.configure(text=f"p1:\np2:")
            else:
                crop_pos = result.boxes.xyxy.cpu().numpy()
                self.position_label.configure(text=f"p1:({round(float(crop_pos[0][0]))},{round(float(crop_pos[0,1]),3)})\np2:({round(float(crop_pos[0][1]),3)},{round(float(crop_pos[0][3]),3)})")
                #裁切圖片
                crop_img = Image.fromarray(frame).crop(
                    (
                        crop_pos[0][0],
                        crop_pos[0][1],
                        crop_pos[0][2],
                        crop_pos[0][3]
                    ))
                self.display_rembg_image(crop_img)
            
            
            # 每 10 毫秒更新一次畫面
            self.after(20, self.update_frame)

    def display_origin_image(self, img):
        self.origin_img = ImageTk.PhotoImage(image=img)
        self.mango_origin_img.configure(image=self.origin_img)
        
    def display_rembg_image(self, img:Image):
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        rembg_bytes = remove(buffer.getvalue()) #輸出為bytes
        img = Image.open(BytesIO(rembg_bytes))
        
        self.rembg_img = ImageTk.PhotoImage(image=img)
        self.mango_rembg_img.configure(image=self.rembg_img)
        
        #呼叫灰階
        self.display_gray_image(rembg_bytes)
    
    def display_gray_image(self, img):
        
        np_img = np.frombuffer(img,dtype=np.uint8)
        np_img = cv2.imdecode(np_img, cv2.IMREAD_COLOR)
        gray_img = cv2.cvtColor(np_img, cv2.COLOR_BGR2GRAY)
        
        pil_img = Image.fromarray(gray_img)
        
        self.gray_img = ImageTk.PhotoImage(image=pil_img)
        self.mango_gray_img.configure(image=self.gray_img)
        
    def display_black_image(self, img,ths=60):
        
        _, ths_img = cv2.threshold(img, ths, 255, cv2.THRESH_BINARY)
        
        black_dot = cv2.bitwise_and(img,ths_img)
        pil_black_img = Image.fromarray(black_dot)
        self.black_img = ImageTk.PhotoImage(image=pil_black_img)
        self.mango_black_img.configure(image=self.black_img)


    def on_closing(self):
        """關閉窗口時的清理工作"""
        print("關閉視窗，釋放資源中...")
        self.model = None
        self.stop_camera()
        self.destroy()




if __name__ == "__main__":
    app = YOLOApp()
    app.mainloop()
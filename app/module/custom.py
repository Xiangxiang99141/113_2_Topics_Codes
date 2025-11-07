from io import BytesIO
import numpy as np
from PIL import Image,ImageQt
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

def covert_to_Qpixmap(img:np.ndarray|BytesIO,size:dict):
    match type(img):
        case np.ndarray:
            # img = cv2.resize(img,resize)
            pimg = Image.fromarray(img)
        case _:
            pimg = Image.open(img) 
    qimg = ImageQt.toqimage(pimg)   # 轉換成 Qt 使用的圖片格式
    canvas = QPixmap().fromImage(qimg).scaled(size["width"]-10,size["height"]-10,Qt.AspectRatioMode.KeepAspectRatio) # 建立 QPixmap 畫布，讀取圖片
    return canvas
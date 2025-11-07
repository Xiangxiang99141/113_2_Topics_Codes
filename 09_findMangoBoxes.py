from ultralytics import YOLO
from pathlib import Path
import cv2 as cv
import numpy as np

classesList = ['A','B','C']
datasetPath = Path('../datasets/for_Classfication')

def findMangoBoxes(img_list,save_dir):
    model = YOLO('model/mango_detect.pt')
    results = model.predict(img_list)
    for i in range(len(results)):
        path = img_list[i]
        img = cv.imread(str(path))
        # result.show()
        boxes = results[i].boxes.xyxy.cpu().numpy().astype(int)
        print(f'boxes:{boxes}')
        # 框出芒果區塊並製作mask
        mask = np.zeros(img.shape[:2],dtype=np.uint8)
        
        for (x1,y1,x2,y2) in boxes:
            mask[y1:y2,x1:x2] = 255
        
        out = img.copy()
        out[mask==0] = (0,0,0)
        #製作父級目錄(train or val)
        parent_name = path.parent.name
        final_save_dir = save_dir / parent_name
        final_save_dir.mkdir(parents=True, exist_ok=True)
        #儲存凸顯後的圖片
        cv.imwrite(str(final_save_dir / path.name),out)
        print(f'{path.name} 芒果凸顯完成')
        # cv.imshow('結果',out)

        # cv.waitKey(0)
if __name__ == '__main__':
    for c in classesList:
        imgPath = datasetPath/f'{c}'
        img_list = list(imgPath.rglob('**/*.jpg'))
        # print(img_list)
        save_dir = datasetPath / f'{c}_bgBlack_boxs'
        save_dir.mkdir(parents=True,exist_ok=True)
        print(f'{c} 類芒果偵測中')
        findMangoBoxes(img_list,save_dir)
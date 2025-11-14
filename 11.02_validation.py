from ultralytics import YOLO


def vaildation():
    model = YOLO(r"Mango_training\mango_classification_2025-11-13-11.13.12\weights\best.pt")
    metric = model.val(
        data=r"D:\大學\專題\影像辨識芒果\app\mango_dataset\train",
        project="Mango_valdation",
        name="classfication_for_inside",
        imgsz=224,
        device=0,
        verbose=True
    )

    print(metric)

if __name__ =='__main__':
    vaildation()
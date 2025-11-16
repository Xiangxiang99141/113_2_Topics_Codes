from ultralytics import YOLO


def vaildation():
    model = YOLO(r"model\mango_detect.pt")
    metric = model.val(
        # data=r"D:\大學\專題\影像辨識芒果\app\mango_dataset\train",
        project="Mango_valdation",
        name="object_detection",
        imgsz=640,
        device=0,
        verbose=True
    )

    print(metric)

if __name__ =='__main__':
    vaildation()
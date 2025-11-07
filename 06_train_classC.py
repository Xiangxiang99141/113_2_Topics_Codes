from ultralytics import YOLO
from pathlib import Path
from datetime import datetime,timezone,timedelta


def main():
    weights_path = "model/Coco.pt"  # use yolo11n.pt for a small model
    dataset_yaml = "../datasets/trainC/dataset.yaml"
    model = YOLO(weights_path, task="detect")

    # 設定台灣時區 
    tz = timezone(timedelta(hours=8)) 
    now = datetime.now(tz)
    # Define your additional arguments here
    batch = 10
    project = "Mango_dot"
    epochs = 100
    project_name = now.strftime("%Y-%m-%d-%H.%M.%S")
    # print(k,dataset_yaml)
    # model = YOLO(weights_path, task="detect")
    results = model.train(
        data=dataset_yaml, 
        epochs=epochs,
        batch=batch, #同時學習四張照片
        device=0, #使用GPU 0 
        imgsz=640,
        project=project,
        name=f"{project_name}/mango_classC"
    )  # include any additional train arguments

if __name__ == "__main__":
    main()
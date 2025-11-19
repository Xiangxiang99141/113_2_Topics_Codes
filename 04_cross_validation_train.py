from ultralytics import YOLO
from pathlib import Path
from datetime import datetime

# weights_path = "model\Coco.pt"  # use yolo11n.pt for a small model
weights_path = "model\yolo11n-seg.pt"  # use yolo11n.pt for a small model
datasets_path_for_train = "../datasets/2025-11-20-01.05.34_6-Fold_Cross-val"
model = YOLO(weights_path)

results = {}

def train():
    # Define your additional arguments here
    batch = 10
    project = "Mango_dot"
    epochs = 100
    project_name = datetime.today().strftime("%Y-%m-%d-%H.%M.%S")
    datasets = sorted(Path(datasets_path_for_train).rglob("*.yaml"))
    for k, dataset_yaml in enumerate(datasets):
        print(dataset_yaml)
        # model = YOLO(weights_path, task="detect")
        results[k] = model.train(
            data=dataset_yaml, 
            epochs=epochs,
            batch=batch, #同時學習四張照片
            device=0, #使用GPU 0 
            imgsz=640,
            project=project,
            name=f"{project_name}/mango_dot_fold_{k + 1}"
        )  # include any additional train arguments
    
    
if __name__ == "__main__":
    train()
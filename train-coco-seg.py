#seg

#https://docs.ultralytics.com/zh/datasets/segment/coco/#usage

if __name__ == "__main__":

    from ultralytics import YOLO

    # Load a model
    model = YOLO("model/yolo11n-seg.pt")  # load a pretrained model (recommended for training)

    # Train the model
    results = model.train(  data="config/coco.yaml", 
                            epochs=100,
                            batch=8, #同時學習四張照片
                            device=0, #使用GPU 0 
                            imgsz=640,
                            project="Coco",
                            name="train-1-seg"
                        )
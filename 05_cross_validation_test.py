from ultralytics import YOLO
from datetime import datetime
date = datetime.today().strftime("%Y-%m-%d-%H.%M.%S")

model_path = ["Mango_dot/2025-08-21-09.56.17/mango_dot_fold_1/weights/best.pt",
            "Mango_dot/2025-08-21-09.56.17/mango_dot_fold_2/weights/best.pt",
            "Mango_dot/2025-08-21-09.56.17/mango_dot_fold_3/weights/best.pt",
            "Mango_dot/2025-08-21-09.56.17/mango_dot_fold_4/weights/best.pt",
            "Mango_dot/2025-08-21-09.56.17/mango_dot_fold_5/weights/best.pt"]
for i in range(len(model_path)):
    model = YOLO(model_path[i])

    model.predict(f"../datasets/2025-08-20-17.41.05_5-Fold_Cross-val/split_{i+1}/test/images",
                device=0,batch=16,project="Mango_predict",name=f'{date}_5_fold_split_{i+1}'
                ,save=True,save_txt=True)
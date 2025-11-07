from ultralytics import YOLO
from datetime import datetime
from pathlib import Path

# c = ["classA","classB","classC"]
c = ["A","B","C"]
model_list = ["Mango_training/mango_classification","Mango_training/mango_classification_rembg_20251011"]
# model = YOLO("Mango_dot/2025-08-21-15.40.51/mango_classC/weights/best.pt")
# model = YOLO("")
# model = YOLO("/weights/best.pt")
for m in model_list:
    path = Path(m)
    model = YOLO(path / "weights/best.pt")
    date = datetime.today().strftime("%Y-%m-%d-%H.%M.%S")
    # for i in c:
    #     model.predict(
    #         # f"../datasets/{i}",
    #         f"../datasets/for_Classfication/ori/{i}/train",
    #         device=0,batch=16,
    #         # conf=0.5,
    #         project="Mango_predict",
    #         name=f'{date}_{i}_{path.name}',
    #         save=True,save_txt=True
    #     )
    model.predict(
        # f"../datasets/{i}",
        f"../datasets/for_predict/inside",
        device=0,batch=16,
        # conf=0.5,
        project="Mango_predict",
        name=f'{date}_inside_{path.name}',
        save=True,save_txt=True
    )
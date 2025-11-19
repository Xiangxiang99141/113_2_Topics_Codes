#載入數據
from pathlib import Path
import pandas as pd
import yaml
from collections import Counter

dataset_path = Path("./my_dataset/mangoV6")  # replace with 'path/to/dataset' for your custom data
labels = sorted(dataset_path.rglob("*labels/*.txt"))  # all data in 'labels'

#讀取Yaml文件
yaml_file = "config/dataset_for_cross_vaildation.yaml"

with open (yaml_file,encoding="utf-8") as y:
    classes = yaml.safe_load(y)["names"] #讀取yaml 的類別名稱
cls_idx = sorted(classes.keys())
# print(cls_idx)

#初始化dataframe
index  = [label.stem for label in labels] #抓取檔案名稱
# print(index)
labels_df = pd.DataFrame([],columns=cls_idx,index=index)

#計算每個類別的標籤數量
for label in labels:
    lbl_counter = Counter()
    
    with open(label) as lf:
        lines = lf.readlines()
    for line in lines:
        #YOLO 格式的 label 類別在每一列第一個位置
        lbl_counter[int(line.split(" ",1)[0])] =+ 1
    labels_df.loc[label.stem] = lbl_counter
    
labels_df = labels_df.fillna(0.0) #把無效的值填0
print(labels_df)

#將數據拆分成K份
import random

from sklearn.model_selection import KFold

random.seed(0)  # for reproducibility
ksplit = 6
kf = KFold(n_splits=ksplit, shuffle=True, random_state=20)  # setting random_state for repeatable results

kfolds = list(kf.split(labels_df))
#建立DataFrame展示分類結果
folds = [f"split_{n}" for n in range(1, ksplit + 1)]
folds_df = pd.DataFrame(index=index, columns=folds)

for i, (train, test) in enumerate(kfolds, start=1):
    folds_df[f"split_{i}"].loc[labels_df.iloc[train].index] = "train"
    folds_df[f"split_{i}"].loc[labels_df.iloc[test].index] = "val"
    
print(folds_df)

#計算標籤分佈-理想各分哥的標籤數量需一樣
fold_lbl_distrb = pd.DataFrame(index=folds, columns=cls_idx)

for n, (train_indices, val_indices) in enumerate(kfolds, start=1):
    train_totals = labels_df.iloc[train_indices].sum()
    val_totals = labels_df.iloc[val_indices].sum()

    # 避免除以0
    ratio = val_totals / (train_totals + 1e-7)
    fold_lbl_distrb.loc[f"split_{n}"] = ratio
    
#創建資料夾跟 datasets
import datetime

supported_extensions = [".jpg", ".jpeg", ".png"]

# Initialize an empty list to store image file paths
images = []

# Loop through supported extensions and gather image files
for ext in supported_extensions:
    images.extend(sorted((dataset_path / "images").rglob(f"*{ext}")))

date = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime("%Y-%m-%d-%H.%M.%S")


# Create the necessary directories and dataset YAML files
child_path = f"{date}_{ksplit}-Fold_Cross-val"
save_path = Path(f"../datasets/{child_path}")
save_path.mkdir(parents=True, exist_ok=True)
ds_yamls = []

for split in folds_df.columns:
    # Create directories
    split_dir = save_path / split
    split_dir.mkdir(parents=True, exist_ok=True)
    (split_dir / "train" / "images").mkdir(parents=True, exist_ok=True)
    (split_dir / "train" / "labels").mkdir(parents=True, exist_ok=True)
    (split_dir / "val" / "images").mkdir(parents=True, exist_ok=True)
    (split_dir / "val" / "labels").mkdir(parents=True, exist_ok=True)

    # Create dataset YAML files
    dataset_yaml = split_dir / f"{split}_dataset.yaml"
    ds_yamls.append(dataset_yaml)

    with open(dataset_yaml, "w") as ds_y:
        yaml.safe_dump(
            {
                "path": f"{child_path}/{split}/train",
                "train": "train",
                "val": "val",
                # "test": "test",
                "names": classes,
            },
            ds_y,
        )
        
#將照片分類放入
import shutil
from tqdm import tqdm

for image, label in tqdm(zip(images, labels), total=len(images), desc="Copying files"):
    for split, k_split in folds_df.loc[image.stem].items():
        # Destination directory
        img_to_path = save_path / split / k_split / "images"
        lbl_to_path = save_path / split / k_split / "labels"

        # Copy image and label files to new directory (SamefileError if file already exists)
        shutil.copy(image, img_to_path / image.name)
        shutil.copy(label, lbl_to_path / label.name)
        
#儲存紀錄
folds_df.to_csv(save_path / "kfold_datasplit.csv")
fold_lbl_distrb.to_csv(save_path / "kfold_label_distribution.csv")
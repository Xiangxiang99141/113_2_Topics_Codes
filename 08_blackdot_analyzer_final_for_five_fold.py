
import cv2
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
import pandas as pd
from pathlib import Path
from zipfile import ZipFile
from PIL import Image
import os
from datetime import datetime

matplotlib.rcParams['font.sans-serif'] = ['Microsoft JhengHei']  # 指定中文字型
matplotlib.rcParams['axes.unicode_minus'] = False

ALLOWED_LABELS = {
    0: "mango",       # 芒果
    1: "blackdot",     # 黑點
    2: "瑕疵"
}


def compute_and_annotate(image_input_folder="images",
                         label_input_folder="labels",
                         output_folder="output", export_zip=True):
    image_dir = Path(image_input_folder)
    label_dir = Path(label_input_folder)
    output_dir = Path(output_folder)
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []

    for img_path in sorted(image_dir.glob("*.jpg")):
        # txt_path = img_path.with_suffix(".txt")
        print(f"計算 {img_path.name} 資訊中...")
        txt_path = label_dir/f"{img_path.stem}.txt"
        if not txt_path.exists():
            print("label檔未存在")
            continue
        image = cv2.imread(str(img_path))
        h, w = image.shape[:2]

        mango_area = 0
        blackdot_area = 0
        flaw_area = 0 #瑕疵面積

        with open(txt_path, "r") as f:
            for line in f.readlines():
                parts = list(map(float, line.strip().split()))
                # 跳過 bbox 格式 (len == 5)
                if len(parts) == 5:
                    continue
                label = int(parts[0])
                
                if label not in ALLOWED_LABELS:
                    continue  # 過濾掉非 mango/blackdot
                
                points = np.array(parts[1:], dtype=np.float32).reshape(-1, 2)
                abs_points = np.stack([points[:, 0] * w, points[:, 1] * h], axis=1)
                area = cv2.contourArea(abs_points.astype(np.int32))
                if label == 0:
                    mango_area += area
                elif label == 1:
                    blackdot_area += area
                elif label == 2:
                    flaw_area += area

        percent = (blackdot_area / mango_area * 100) if mango_area > 0 else 0
        results.append((img_path.name, mango_area, blackdot_area, round(percent, 2),flaw_area))

        save_path = output_dir / f"{img_path.stem}_annotated.jpg"
        data = {
            'percent':percent,
            'mango_area':mango_area,
            'blackdot_area':blackdot_area,
            'flaw_area':flaw_area
        }
        print("儲存結果")
        save_annotated_image(img_path, txt_path,save_path,data)

    df = pd.DataFrame(results, columns=["圖片名稱", "芒果面積", "黑點面積", "黑點占比 (%)","瑕疵面積"])
    df.to_csv(output_dir / "統計結果.csv", index=False, encoding="utf-8-sig")

    if export_zip:
        zip_path = output_dir.with_suffix(".zip")
        with ZipFile(zip_path, "w") as zipf:
            for file in output_dir.glob("*"):
                zipf.write(file, arcname=file.name)
        print(f"已匯出 ZIP：{zip_path}")
    else:
        print(f"分析完成，圖與統計存於：{output_dir}")

def save_annotated_image(img_path, txt_path, save_path,data):
    image = cv2.imread(str(img_path))
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    h, w = image.shape[:2]

    mango_pts = []
    blackdot_pts = []
    flaw_pts = []

    with open(txt_path, "r") as f:
        for line in f.readlines():
            parts = list(map(float, line.strip().split()))
            print(parts,end="\r\n")
            # 跳過 bbox 格式 (len == 5)
            if len(parts) == 5:
                print("bbox格式跳過")
                continue
            
            label = int(parts[0])
            
            if label not in ALLOWED_LABELS:
                    continue  # 過濾掉非 mango/blackdot
                
            points = np.array(parts[1:], dtype=np.float32).reshape(-1, 2)
            abs_points = np.stack([points[:, 0] * w, points[:, 1] * h], axis=1).astype(np.int32)

            if label == 0:
                mango_pts.append(abs_points)
            elif label == 1:
                blackdot_pts.append(abs_points)
            elif label ==2:
                flaw_pts.append(abs_points)
                
    tmp_path = save_path.with_suffix(".png")
    plt.figure(figsize=(8, 8))
    plt.imshow(image)
    plot_polygon(mango_pts,"lime","mango")
    plot_polygon(blackdot_pts,"red","blackdot")
    plot_polygon(flaw_pts,"blue","瑕疵")
    # for pts in mango_pts:
    #     plt.plot(*zip(*np.concatenate([pts, pts[:1]])), color="lime", linewidth=2, label="mango" if 'mango' not in plt.gca().get_legend_handles_labels()[1] else "")
    # for pts in blackdot_pts:
    #     plt.plot(*zip(*np.concatenate([pts, pts[:1]])), color="red", linewidth=2, label="blackdot" if 'blackdot' not in plt.gca().get_legend_handles_labels()[1] else "")

    # 中文圖標資訊：黑點占比、面積資訊
    plt.title(f"{img_path.name}\n黑點占比：{data['percent']:.2f}%\n芒果面積：{data['mango_area']:.0f} 像素，黑點面積：{data['blackdot_area']:.0f} 像素，瑕疵面積：{data['flaw_area']}像素", fontsize=13)
    plt.legend()
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(tmp_path, dpi=80)
    plt.close()

    with Image.open(tmp_path) as im:
        rgb_im = im.convert("RGB")
        rgb_im.save(save_path, "JPEG", quality=85)
    os.remove(tmp_path)

def plot_polygon(ptss,color:str,label):
    for pts in ptss:
        plt.plot(*zip(*np.concatenate([pts, pts[:1]])), color=color, linewidth=2, label=label if label not in plt.gca().get_legend_handles_labels()[1] else "")

if __name__ == "__main__":
    # base_path = "Mango_predict"
    # name = "2025-08-21-14.13.20_5_fold_split_"
    output_dir_date = datetime.now().strftime("%Y%m%d")
    # folders=[
    #     {
    #         "images":"../datasets/2025-08-20-17.41.05_5-Fold_Cross-val/split_1/test/images",
    #         "labels":"Mango_predict/2025-08-21-14.13.20_5_fold_split_1/labels"
    #     },
    #     {
    #         "images":"../datasets/2025-08-20-17.41.05_5-Fold_Cross-val/split_2/test/images",
    #         "labels":"Mango_predict/2025-08-21-14.13.20_5_fold_split_2/labels"
    #     },
    #     {
    #         "images":"../datasets/2025-08-20-17.41.05_5-Fold_Cross-val/split_3/test/images",
    #         "labels":"Mango_predict/2025-08-21-14.13.20_5_fold_split_3/labels"
    #     },
    #     {
    #         "images":"../datasets/2025-08-20-17.41.05_5-Fold_Cross-val/split_4/test/images",
    #         "labels":"Mango_predict/2025-08-21-14.13.20_5_fold_split_4/labels"
    #     },
    #     {
    #         "images":"../datasets/2025-08-20-17.41.05_5-Fold_Cross-val/split_5/test/images",
    #         "labels":"Mango_predict/2025-08-21-14.13.20_5_fold_split_5/labels"
    #     }
    # ]
    folders = [
        {
            "images":"../datasets/classA",
            "labels":"../datasets/classA/labels"
        },
        {
            "images":"../datasets/classB",
            "labels":"Mango_predict/2025-08-22-16.37.14_classB/labels"
        }
    ]
    for i in range(len(folders)):
        compute_and_annotate(
            image_input_folder=folders[i]['images'],
            label_input_folder=folders[i]['labels'],
            # output_folder=f"../test/訓練偵測測試/{output_dir_date}/YOLO/model_{i+1}",
            output_folder=f"../test/訓練偵測測試/{output_dir_date}/YOLO/class_{i+1}",
            export_zip=False
        )

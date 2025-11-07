
from pathlib import Path
from zipfile import ZipFile
from PIL import Image
from datetime import datetime
import cv2
import matplotlib.pyplot as plt
import matplotlib

import numpy as np
import pandas as pd
import os

matplotlib.rcParams['font.sans-serif'] = ['Microsoft JhengHei']  # 指定中文字型
matplotlib.rcParams['axes.unicode_minus'] = False

ALLOWED_LABELS = {
    0: "mango",       # 芒果
    1: "blackdot",     # 黑點
    2: "瑕疵"
}



def compute_and_annotate(input_folder="images", input_label_dir="label",output_folder="output", export_zip=True):
    image_dir = Path(input_folder)
    label_dir = Path(input_label_dir)
    output_dir = Path(output_folder)
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []

    for img_path in sorted(image_dir.glob("*.jpg")):
        # txt_path = img_path.with_suffix(".txt")
        txt_path = label_dir.joinpath("labels",f"{img_path.stem}.txt")
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
        results.append((img_path.name, mango_area, blackdot_area, round(percent, 2)))

        save_path = output_dir / f"{img_path.stem}_annotated.jpg"
        save_annotated_image(img_path, txt_path, percent, save_path, mango_area, blackdot_area)

    df = pd.DataFrame(results, columns=["圖片名稱", "芒果面積", "黑點面積", "黑點占比 (%)"])
    df.to_csv(output_dir / "統計結果.csv", index=False, encoding="utf-8-sig")

    if export_zip:
        zip_path = output_dir.with_suffix(".zip")
        with ZipFile(zip_path, "w") as zipf:
            for file in output_dir.glob("*"):
                zipf.write(file, arcname=file.name)
        print(f"已匯出 ZIP：{zip_path}")
    else:
        print(f"分析完成，圖與統計存於：{output_dir}")

def save_annotated_image(img_path, txt_path, percent, save_path, mango_area, blackdot_area,flaw_area):
    image = cv2.imread(str(img_path))
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    h, w = image.shape[:2]

    mango_pts = []
    blackdot_pts = []
    flaw_pts = []

    with open(txt_path, "r") as f:
        for line in f.readlines():
            parts = list(map(float, line.strip().split()))
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
    
    plot_polygons(mango_pts,"lime","mango")
    plot_polygons(blackdot_pts,"red","mango")
    plot_polygons(flaw_pts,"blue","mango")
    
    # for pts in mango_pts:
    #     plt.plot(*zip(*np.concatenate([pts, pts[:1]])), color="lime", linewidth=2, label="mango" if 'mango' not in plt.gca().get_legend_handles_labels()[1] else "")
    # for pts in blackdot_pts:
    #     plt.plot(*zip(*np.concatenate([pts, pts[:1]])), color="red", linewidth=2, label="blackdot" if 'blackdot' not in plt.gca().get_legend_handles_labels()[1] else "")

    # 中文圖標資訊：黑點占比、面積資訊
    plt.title(f"{img_path.name}\n黑點占比：{percent:.2f}%\n芒果面積：{mango_area:.2f} 像素，黑點面積：{blackdot_area:.2f} 像素，瑕疵面積：{flaw_area:.2f}", fontsize=13)
    plt.legend()
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(tmp_path, dpi=80)
    plt.close()

    with Image.open(tmp_path) as im:
        rgb_im = im.convert("RGB")
        rgb_im.save(save_path, "JPEG", quality=85)
    os.remove(tmp_path)

def plot_polygons(polygons, color, label):
    for pts in polygons:
        x, y = zip(*np.concatenate([pts, pts[:1]]))
        plt.plot(x, y, color=color, linewidth=2,
                label=label if label not in plt.gca().get_legend_handles_labels()[1] else "")
                #判斷是否已經劃上這個類別的的框




if __name__ == "__main__":
    base_path = "my_datasets"
    name = "MangoV5"
    date = datetime.today().strftime("%Y-%m-%d-%H.%M.%S")
    compute_and_annotate(
        input_folder=f"my_datasets/MangoV5/images", #導入原始圖片路徑
        input_label_dir=f"{base_path}/{name}",
        output_folder=f"訓練偵測測試/classC_{date}",
        export_zip=False
    )

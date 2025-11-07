from pathlib import Path
import matplotlib.pyplot as plt

base_folder = Path('Mango_predict')

class_list = ['A', 'B', 'C']
conf_min = 6
conf_max = 9
conf_step = 1
conf_multiple = 10

save_dir = Path("Mango_class_results")
save_dir.mkdir(exist_ok=True)


def calc_conf_curve(folder_name, currect_class,thresholds):
    """計算指定資料夾在不同 conf 下的正確率"""
    folder = base_folder / folder_name / 'labels'
    labels = list(folder.glob('*.txt'))

    conf_list = {}
    for i in thresholds:
        class_dir = {'A': 0, 'B': 0, 'C': 0}
        for label in labels:
            with open(label) as f:
                line = f.readline().strip().split()
                if len(line) < 2:
                    continue
                confidence = float(line[0])
                cls = line[1]
                if confidence > i:
                    class_dir[cls] += 1
        conf_list[i ] = (class_dir[currect_class] / len(labels)) * 100
    return conf_list


if __name__ == '__main__':
    # 把資料夾依類別分組
    thresholds = [i / 10 for i in range(6, 10)]
    grouped_folders = {
        "A": [
            '2025-09-21-17.45.35_classA_mango_classification',
            '2025-09-21-17.47.05_classA_mango_classification_bgBlack_boxs'
        ],
        "B": [
            '2025-09-21-17.45.35_classB_mango_classification',
            '2025-09-21-17.47.05_classB_mango_classification_bgBlack_boxs'
        ],
        "C": [
            '2025-09-21-17.45.35_classC_mango_classification',
            '2025-09-21-17.47.05_classC_mango_classification_bgBlack_boxs'
        ]
    }

    for cls, folders in grouped_folders.items():
        plt.figure(figsize=(6, 4))

        for idx, folder_name in enumerate(folders):
            conf_curve = calc_conf_curve(folder_name, cls,thresholds)
            x = list(conf_curve.keys())
            y = list(conf_curve.values())
            print(f'{cls}:{conf_curve}')
            
            linestyle = '-' if idx == 0 else '--'
            label = f"{cls}" if "bgBlack" not in folder_name else f"{cls}_bgBlack"
            plt.plot(x, y, marker='o', linestyle=linestyle, label=label)

        plt.title(f'Class {cls} - Confidence vs Accuracy')
        plt.xlabel('Confidence threshold')
        plt.ylabel('Accuracy (%)')
        plt.ylim(0, 100)
        plt.grid(True, linestyle='--', alpha=0.6)
        plt.legend()
        plt.tight_layout()

        # 存檔
        save_path = save_dir / f"class{cls}_compare.png"
        plt.savefig(save_path, dpi=300)
        plt.close()

        print(f"✅ 圖片已儲存: {save_path}")

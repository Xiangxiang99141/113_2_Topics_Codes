from backgroundremover.bg import remove
from pathlib import Path

from backgroundremover.bg import remove

def remove_bg(src_img_path, out_img_path):
    # model_choices = ["u2net", "u2net_human_seg", "u2netp"]
    f = open(src_img_path, "rb")
    data = f.read()
    img = remove(data,
                background_color=(255,255,255))
    f.close(),
    f = open(out_img_path, "wb")
    f.write(img)
    f.close()

base_folder = Path(r'D:\大學\專題\影像辨識芒果\datasets\for_Classfication')
path = [
    Path(r'D:\大學\專題\影像辨識芒果\datasets\for_Classfication\ori\A'),
    Path(r'D:\大學\專題\影像辨識芒果\datasets\for_Classfication\ori\B'),
    Path(r'D:\大學\專題\影像辨識芒果\datasets\for_Classfication\ori\C')
]
new_rembg = base_folder / "rembg_1125"
new_rembg.mkdir(exist_ok=True)

for f in path:
    for c in [f/"train",f/"val"]:
        save_dir = new_rembg / f.name / c.name
        save_dir.mkdir(parents=True,exist_ok=False)
        print(save_dir)
        images = c.rglob('*.jpg')
        for img in images:
            save_path_img = save_dir / img.name
            # print(save_path_img)
            remove_bg(img,save_dir/save_path_img)
        
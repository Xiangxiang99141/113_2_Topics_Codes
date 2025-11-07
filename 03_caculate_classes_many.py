#很多檔案用

from pathlib import Path
from datetime import datetime, timedelta, timezone
import pandas as pd

childDirList = ["train","test"]

def caculate(base:Path,classes:str):
    childs = base.iterdir()
    _classes = [{"title":"label","count":0}]
    
    

    # 設定台灣時區
    tz = timezone(timedelta(hours=8))
    now = datetime.now(tz)
    date = now.strftime("%Y-%m-%d-%H.%M.%S")  # 注意這裡用 - 避免檔名冒號錯誤
    output_dir = Path("class_count")
    output_dir.mkdir(exist_ok=True)
    
    #輸出程excel
    output_path = output_dir /f"class_count_{date}-five-fold.xlsx"
    
    with open(f"{classes}/classes.txt",encoding="utf-8") as f:
        for line in f.readlines():
            line = line.strip()
            _classes.append({"title":line,"count":0})
        print(_classes)
    
    with pd.ExcelWriter(output_path) as writer:
        for child in childs:
            if not child.is_dir():
                continue
            
            for l in childDirList:
                #重製為0
                t = child / l
                labelsPath = t / "labels"
                labels = labelsPath.glob("*.txt")
                labelCount = 0
                for i in _classes:
                    i["count"]=0
                    
                for label in labels:
                    labelCount+=1
                    with open(label) as f:
                        for line in f.readlines():
                            line = line.strip()
                            splitLine = line.split(" ")
                            c = _classes[int(splitLine[0])+1]
                            c["count"]+=1
                    
                _classes[0]["count"] = labelCount
                foldName = f"{child.name}-{l}"
                print(f"{foldName}:{classes}")
                print(f"count:{_classes}")
                
                # 轉成 DataFrame
                df = pd.DataFrame(_classes).T
                df.columns = range(len(df.columns))  # 改成 0,1,2,3...
                print(df)
                df.to_excel(writer,sheet_name=foldName, index=True)  # index=True 保留 title、count
    print(f"已輸出到 {output_path.resolve()}")

if __name__ == "__main__":
    classes_path = "my_dataset/mangoV5"
    base_path = Path("datasets/2025-08-20-17.41.05_5-Fold_Cross-val")
    caculate(base_path,classes_path)
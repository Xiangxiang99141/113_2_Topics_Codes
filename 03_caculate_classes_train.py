#很多檔案用

from pathlib import Path
from datetime import datetime, timedelta, timezone
import pandas as pd
import re

childDirList = ["train","test"]
autosplitPath = ["train","val"]
def caculate(base:Path,classes:str):
    #找到子資料夾(split1、split2...)
    childs = base.iterdir()
    _classes = [{"title":"label","count":0}]
    
    

    # 設定台灣時區
    tz = timezone(timedelta(hours=8))
    now = datetime.now(tz)
    date = now.strftime("%Y-%m-%d-%H.%M.%S")  # 注意這裡用 - 避免檔名冒號錯誤
    output_dir = Path("class_count")
    output_dir.mkdir(exist_ok=True)
    
    #輸出程excel檔名
    output_path = output_dir /f"class_count_{date}-five-fold.xlsx"
    
    with open(f"{classes}/classes.txt",encoding="utf-8") as f:
        for line in f.readlines():
            line = line.strip()
            #加入classes
            _classes.append({"title":line,"count":0})
        print(_classes)
    
    with pd.ExcelWriter(output_path) as writer:
        #遍例每個Split
        for child in childs:
            if not child.is_dir():
                continue
            
            #train dir test dir
            for l in childDirList:
                #重製為0
                labels = []
                if l=="train":
                    #使用autosplit檔案區分train跟val資料集數量
                    for splitName in autosplitPath:
                        labels = findLabelList(child / l,splitName)
                        fold_name = f"{child.name}-{splitName}"
                        caculateClassesCount(writer,fold_name,_classes,labels)
                # labels = labelsPath.glob("*.txt")
                # t = child / l
                elif l=="test":
                    labels = (child / "test/labels").glob("*.txt")
                    fold_name = f"{child.name}-{l}"
                    caculateClassesCount(writer,fold_name,_classes,labels)
    
    print(f"已輸出到 {output_path.resolve()}")

def findLabelList(childDir:Path,spiltFileName:str):
    txt_path = childDir/f"autosplit_{spiltFileName}.txt"
    if not txt_path.exists():
        print(f"警告：找不到 {txt_path}")
        return []
    
    tmp = []
    with open(txt_path) as fileList:
        for line in fileList.readlines():
            #找到檔名id
            match = re.search(r"images/(.+?)\.jpg", line)
            if match:
                filename = match.group(1)
                # print(filename)  # cf266d64-01328
                #建造lable path
                pathName = childDir/"labels"/f"{filename}.txt"
                tmp.append(pathName)
    return tmp

def caculateClassesCount(writer,foldName,classes,labels):
    labelCount = 0
    for i in classes:
        i["count"]=0
        
    for label in labels:
        labelCount+=1
        print(f"計算 {label} 各類別數量中")
        with open(label) as f:
            for line in f.readlines():
                line = line.strip()
                splitLine = line.split(" ")
                #找到他是哪個類別
                c = classes[int(splitLine[0])+1]
                c["count"]+=1
        
    classes[0]["count"] = labelCount
    # foldName = f"{child.name}-{splitName}"
    print(f"{foldName}:{classes}")
    print(f"count:{classes}")

    # 轉成 DataFrame
    df = pd.DataFrame(classes).T
    df.columns = range(len(df.columns))  # 改成 0,1,2,3...
    print(df)
    df.to_excel(writer,sheet_name=foldName, index=True)  # index=True 保留 title、count

if __name__ == "__main__":
    classes_path = "my_dataset/mangoV5"
    base_path = Path("../datasets/2025-08-20-17.41.05_5-Fold_Cross-val")
    caculate(base_path,classes_path)
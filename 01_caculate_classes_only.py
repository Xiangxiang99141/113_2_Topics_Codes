from pathlib import Path
from datetime import datetime, timedelta, timezone
import pandas as pd


def caculate(classes:str,label:str):
    labelsPath = Path(f"{label}/labels")
    _classes = [{"title":"label","count":0}]
    lableCount=0
    with open(f"{classes}/classes.txt",encoding="utf-8") as f:
        for line in f.readlines():
            line = line.strip()
            _classes.append({"title":line,"count":0})
        print(_classes)
        
    labels = labelsPath.glob("*.txt")
    for label in labels:
        lableCount+=1
        with open(label) as f:
            for line in f.readlines():
                line = line.strip()
                splitLine = line.split(" ")
                c = _classes[int(splitLine[0])+1]
                c["count"]+=1
    _classes[0]["count"] = lableCount
    output(_classes)

def output(data):
        # 轉成 DataFrame
    df = pd.DataFrame(data)
    # 轉置成你要的格式
    df_t = df.T  # 轉置
    df_t.columns = range(len(df_t.columns))  # 改成 0,1,2,3...
    print(df_t)

        # 設定台灣時區
    tz = timezone(timedelta(hours=8))
    now = datetime.now(tz)
    date = now.strftime("%Y-%m-%d-%H.%M.%S")  # 注意這裡用 - 避免檔名冒號錯誤
    output_dir = Path("class_count")
    output_dir.mkdir(exist_ok=True)
    #輸出程excel
    output_path = output_dir /f"class_count_{date}-ori.xlsx"
    df_t.to_excel(output_path, index=True)  # index=True 保留 title、count
    print(f"已輸出到 {output_path.resolve()}")

if __name__ == "__main__":
    classes_path = "my_dataset/mangoV5"
    labels_path = "my_dataset/mangoV5"
    caculate(classes_path,labels_path)
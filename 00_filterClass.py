from pathlib import Path

allowClass = {
    "0":"mango"
}
def main(labelPath):
    path = Path(labelPath)
    labelList = path.glob("*.txt")
    for label in labelList:
        tmp = ""
        with open(label,'r') as f:
            print(f"開啟 {label.name}")
            for line in f.readlines():
                c = line.split(' ')[0]
                if c in allowClass:
                    print("是允許的類別")
                    tmp+=line
            print(tmp)
        with open(f"{label.parent}/{label.stem}-edit.txt",'w') as f:
            f.write(tmp)
            print(f"更新{label.name}完成")




if __name__ == "__main__":
    labelPath = "my_dataset/mangoV5_mangoOnly/labels"
    main(labelPath)
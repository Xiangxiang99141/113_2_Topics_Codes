import cv2
import csv

base_path_label = '.\source\Label_data_Readme'
base_path = '.\source'
dir_name = 'C1-P2_Dev'

#開啟csv檔案
with open(f'{base_path_label}\\{dir_name}.csv', newline='') as csvfile:
    spamreader = csv.reader(csvfile, delimiter=',', quotechar='|')
    i = 1
    spamreader = list(spamreader)
    spamreader.remove(spamreader[0])
    row = spamreader[0]
    print(type(row),row)
    img = cv2.imread(f'{base_path}\\{dir_name}\\{row[0]}')
    
    pt1 = (int(row[2]), int(row[3]))
    pt2 = (int(row[2]) + int(row[4]), int(row[3])+int(row[5]))
    print(type(pt1),pt1)
    #標記選區
    cv2.rectangle(img,pt1,pt2,(0,255,0),2)
    cv2.imshow(f'{row[0]}', img)
    # for row in spamreader:
    #     img = cv2.imread(f'{base_path}\\{dir_name}\\{row[0]}')
    #     cv2.imshow(f'{row[0]}', img)
        # print(i,type(row),row,row[0])
        # i+=1
    #     print(', '.join(row))
    cv2.waitKey(0)
    

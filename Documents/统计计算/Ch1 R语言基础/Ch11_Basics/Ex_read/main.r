## 读取txt文档
data1=read.table("EDUC_SCORES.txt", header=T)  # header = T表示文件的第一行是变量名，也就是列名。
print(data1)

## 读取excel文档
data2=read.csv("weight.csv")
print(data2)

data3=read.csv2("weight.csv")   # 对于用';'分隔的csv文件
print(data3)

## 专门读取excel要用专门的包
## library(readxl)
## data = read_excel("weight.xlsx")
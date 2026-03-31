## 读取txt文档
data1=read.table("EDUC_SCORES.txt", header=T)
print(data1)

## 读取excel文档
data2=read.csv("weight.csv")
print(data2)

data3=read.csv2("weight.csv")
print(data3)


data1=read.table("EDUC_SCORES.txt", header=T)
print(data1)

## 输出txt文档
write.table(data1, "data1.txt")

data2=read.csv("weight.csv")
print(data2)

## 输出csv文档
write.csv(data2, "data2.csv")

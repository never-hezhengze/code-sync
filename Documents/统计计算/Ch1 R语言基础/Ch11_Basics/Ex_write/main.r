data1=read.table("EDUC_SCORES.txt", header=T)
print(data1)

## 输出txt文档
write.table(data1, "data1.txt")

data2=read.csv("weight.csv")
print(data2)

## 输出csv文档
write.csv(data2, "data2.csv")
## 如果希望输出的"data2.csv"文件和weight.csv保持一致，即不输出行号进去，可以运行
## write.csv(data2, "data2.csv", row.names = FALSE)  如果列名里的weight的引号也想去掉，可以再加
## quote = FALSE
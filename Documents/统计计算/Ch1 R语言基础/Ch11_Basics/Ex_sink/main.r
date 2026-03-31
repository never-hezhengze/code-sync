#### source describe statistics function #####
source("data_outline.r")  # 调入程序或函数

#### read data ##############################
weight=read.csv("weight.csv") # 读取数据

#### data analysis ##########################
outline.result=data.outline(weight$weight)
print(outline.result)

#### result output ##########################
sink("weight_outline.txt")   # 输出结果
cat("This is the data outline for a weight data", "\n")
print(outline.result)
sink()  # 关闭后续输出


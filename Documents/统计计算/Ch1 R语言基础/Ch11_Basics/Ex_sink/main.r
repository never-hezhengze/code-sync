#### source describe statistics function #####
source("data_outline.r")  # 调入程序或函数

#### read data ##############################
weight=read.csv("weight.csv") # 读取数据

#### data analysis ##########################
outline.result=data.outline(weight$weight)
print(outline.result)        # 把结果打印在控制台

#### result output ##########################
sink("weight_outline.txt")   # 输出结果，把后面的控制台输出重定向到一个文本文件里
cat("This is the data outline for a weight data", "\n")   # cat()用来输出普通文本
print(outline.result)        # 把结果写入txt文件内
sink()  # 关闭后续输出


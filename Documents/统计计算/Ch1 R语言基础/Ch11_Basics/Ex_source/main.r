#### source describe statistics function #####
source("data_outline.r")  # 调入程序或函数

#### read data ##############################
weight=read.csv("weight.csv") # 读取数据

#### data analysis ##########################
outline.result=data.outline(weight$weight) #用调用的函数分析数据
print(outline.result)


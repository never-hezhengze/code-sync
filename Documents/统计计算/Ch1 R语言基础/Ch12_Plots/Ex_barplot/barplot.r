######## barplot  ####
library(vcd)
Arthritis

table1 = table(Arthritis$Improved)
table1

jpeg("treat1_green_purple.jpeg", height = 760, width = 800, quality = 100)
opar = par(mfrow = c(2, 2))

# 全部改为绿色系和紫色系的组合
barplot(table1, xlab = "Improvement", ylab = "Frequency", 
        col = c("#99CC99", "#66CC66", "#339933"))  # 绿色系

barplot(table1, xlab = "Improvement", ylab = "Frequency", 
        col = c("#CC99FF", "#9966CC", "#663399"))  # 紫色系

barplot(table1, xlab = "Improvement", ylab = "Frequency", 
        col = c("#99CC99", "#CC99FF", "#669966"), horiz = T)  # 混合

barplot(table1, xlab = "Improvement", ylab = "Frequency", 
        col = c("#CCFFCC", "#E6CCFF", "#9966CC"))  # 浅色混合

par(opar)
dev.off()

table2 = table(Arthritis$Improved, Arthritis$Treatment)
table2

jpeg("treat2_green_purple.jpeg", height = 400, width = 1000, quality = 100)
opar = par(mfrow = c(1, 2))

# 改为绿色系和紫色系
barplot(table2, main = "Stacked Barplot", xlab = "Treatment", ylab = "Frequency", 
        col = c("#99CC99", "#66CC66", "#339933"),  # 绿色系
        legend = rownames(table2))

barplot(table2, main = "Grouped Barplot", xlab = "Treatment", ylab = "Frequency", 
        col = c("#CC99FF", "#9966CC", "#663399"),  # 紫色系
        legend = rownames(table2), beside = TRUE)

par(opar)
dev.off()

jpeg("treat3_green_purple_mix.jpeg", height = 400, width = 1000, quality = 100)
opar = par(mfrow = c(1, 2))

# 更丰富的绿色和紫色搭配
barplot(table2, main = "Stacked Barplot", xlab = "Treatment", ylab = "Frequency", 
        col = c("#CCFFCC", "#99CC99", "#669966"),  # 浅绿到深绿
        legend = rownames(table2))

barplot(table2, main = "Grouped Barplot", xlab = "Treatment", ylab = "Frequency", 
        col = c("#E6CCFF", "#CC99FF", "#9966CC"),  # 浅紫到深紫
        legend = rownames(table2), beside = TRUE)

par(opar)
dev.off()

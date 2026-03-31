## 线性回归
# 数据
data(women)
women

# 回归分析
lm.wm<-lm(weight~height,data=women)
print(lm.wm)
summary(lm.wm)

# 泛型函数
coef(lm.wm)
residuals(lm.wm)
AIC(lm.wm)
predict(lm.wm)
names(lm.wm)

# 画图
jpeg("women1.jpeg", height=800, width=800, quality=100)
plot(women$height, women$weight, main = "Women Age 30-39", 
     xlab = "Height (in inches)", ylab = "Weight (in pounds)")
abline(lm.wm)
dev.off()

# 模型调整
lm.wm2 = lm(weight ~ height + I(height^2), data = women)
summary(lm.wm2)

# 画图
jpeg("women2.jpeg", height=800, width=800, quality=100)
plot(women$height, women$weight, main = "Women Age 30-39", 
     xlab = "Height (in inches)", ylab = "Weight (in lbs)")
lines(women$height, fitted(lm.wm2))
dev.off()


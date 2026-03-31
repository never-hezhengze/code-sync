######  QQ     ################################################################################
mydata=read.csv("weight.csv")
w=mydata$weight

jpeg("qq1.jpeg", height=600, width=600, quality = 100)
qqnorm(w)
qqline(w)
dev.off()

mtcars
mpg=mtcars$mpg

jpeg("qq2.jpeg", height=600, width=600, quality = 100)
qqnorm(mpg)
qqline(mpg)
dev.off()


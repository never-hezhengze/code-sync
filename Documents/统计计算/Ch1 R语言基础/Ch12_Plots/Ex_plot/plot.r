## 绘图设备
mydata=read.csv("dose.csv")
mydata

attach(mydata)

plot(dose, drugA)
plot(dose, drugA, type = "b")
plot(dose, drugA, type = "b", lty=4, pch=21, lwd=2, cex=1.5, col="red")

pdf("dose1.pdf")
plot(dose, drugA)
dev.off()

postscript("dose2.eps")
plot(dose, drugA, type = "b")
dev.off()

jpeg("dose3.jpeg", height=600, width=600, quality = 100)
plot(dose, drugA, type = "b", lty=4, pch=21, lwd=2, cex=1.5, col="red")
dev.off()

dev.list()
dev.cur() 
dev.set(4)
dev.off(4)
dev.off()

## 多图显示
##  split.screen
graphics.off() 

split.screen(c(2,1))
split.screen(c(1,3), screen=2)
screen(1)
plot(dose, drugA, type = "b")
screen(3)
plot(dose, drugA, type = "l", lty=1, lwd=1, cex=1, col="red")
screen(4)
plot(dose, drugA, type = "l", lty=2, lwd=2, cex=2, col="blue")
screen(5)
plot(dose, drugA, type = "l", lty=3, lwd=3, cex=3, col="green")
close.screen(all=TRUE)

## layout
mypar = par(no.readonly = TRUE)                   ##存储当前图形设备设置
layout(matrix(c(1,1,2,3), 2, 2, byrow = TRUE))
layout.show(3)
plot(dose, drugA, type = "l", lty=1, lwd=1, cex=1, col="red")
plot(dose, drugA, type = "l", lty=2, lwd=2, cex=2, col="blue")
plot(dose, drugA, type = "l", lty=3, lwd=3, cex=3, col="green")
par(mypar)


## par
jpeg("par.jpeg", height=800, width=800, quality = 100)
opar=par(mfrow=c(2,2))
plot(dose, drugA)
plot(dose, drugA, type = "l", lty=1, lwd=1, cex=1, col="red")
plot(dose, drugA, type = "l", lty=2, lwd=2, cex=2, col="blue")
plot(dose, drugA, type = "l", lty=3, lwd=3, cex=3, col="green")
par(opar)
dev.off()


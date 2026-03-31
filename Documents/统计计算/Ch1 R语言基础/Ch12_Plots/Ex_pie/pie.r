###### pie   #####################################################################################
favor=read.csv("favoriate.csv", header=F)
favor

table3=table(favor)
table3

jpeg("favor.jpeg", height=1200, width=1200, quality = 100)
opar=par(mfrow=c(2,2))
pie(table3)

lab2=paste(names(table3), "\n", table3, sep="")
pie(table3, labels = lab2, col=rainbow(length(table3)))

freq=round(table3/sum(table3)*100)
lab3=paste(names(table3), "\n", freq, "%", sep="")
pie(table3, labels = lab3, 
    col=c("olivedrab2","chartreuse3", "honeydew3", "goldenrod1", "peru"))

freq=round(table3/sum(table3)*100)
lab3=paste(names(table3), "\n", freq, "%", sep="")
pie(table3, labels = lab3, 
    col=heat.colors(5, alpha = 0.4))
par(opar)
dev.off()


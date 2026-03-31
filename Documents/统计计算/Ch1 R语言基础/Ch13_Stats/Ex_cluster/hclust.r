###### data input ################################################
city2015=read.csv("2015city.csv")
rownames(city2015)=city2015[,1]
mydata=city2015[,2:9]

myscale=scale(mydata)
mydist=dist(myscale, diag=T)

###### data analysis #####################################
hc1=hclust(mydist, "single")
hc2=hclust(mydist, "complete")
hc3=hclust(mydist, "median")
hc4=hclust(mydist, "average")
hc5=hclust(mydist, "centroid")
hc6=hclust(mydist, "mcquitty")
hc7=hclust(mydist, "ward.D")
hc8=hclust(mydist, "ward.D2")

###### data plot #####################################
jpeg("city1.jpeg", height=1000, width = 2000, quality = 100)
opar=par(mfrow=c(2,4), mar=c(5.2,4,0,0))
plot(hc1,hang=-1,cex=2)
re1=rect.hclust(hc1,k=5,border="red")

plot(hc2,hang=-1,cex=2)
re2=rect.hclust(hc2,k=5,border="red")

plot(hc3,hang=-1,cex=2)
re3=rect.hclust(hc3,k=5,border="red")

plot(hc4,hang=-1,cex=2)
re4=rect.hclust(hc4,k=5,border="red")

plot(hc5,hang=-1,cex=2)
re5=rect.hclust(hc5,k=5,border="red")

plot(hc6,hang=-1,cex=2)
re6=rect.hclust(hc6,k=5,border="red")

plot(hc7,hang=-1,cex=2)
re7=rect.hclust(hc7,k=5,border="red")

plot(hc8,hang=-1,cex=2)
re8=rect.hclust(hc8,k=5,border="red")
dev.off()


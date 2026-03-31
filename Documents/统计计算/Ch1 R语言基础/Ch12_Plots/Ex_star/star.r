###  stars and faces  ##########################################################################
city2015=read.csv("2015city.csv")
rownames(city2015)=city2015[,1]
mydata=city2015[,2:9]


jpeg("star1.jpeg", height=1000, width=1000, quality = 100)
stars(mydata, full=T)
dev.off()

jpeg("star2.jpeg", height=1000, width=1000, quality = 100)
stars(mydata, full=T, draw.segments=T)
dev.off()

library(aplpack)
jpeg("star3.jpeg", height=1000, width=1000, quality = 100)
faces(mydata, face.type=1)
dev.off()


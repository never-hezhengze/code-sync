library(factoextra)
library(ggplot2)
library(igraph)

###### data input ################################################
city2015=read.csv("2015city.csv")
rownames(city2015)=city2015[,1]
mydata=city2015[,2:9]

### hclust  ########################################
myscale=scale(mydata)
mydist=dist(myscale, diag=T)
myhc=hclust(mydist, method="ward.D") 

### R2 plot ##################################
tss.cal = function(x) sum(scale(x,scale=F)^2)                      
### compute the TSS
wss.cal = function(x,clst) sum(by(x,INDICES=clst,FUN=tss.cal))     
### compute the WSS
rsq.cal = function(x,clst) (tss.cal(x)-wss.cal(x,clst))/tss.cal(x) 
### compute R^2 statistics

rsq = rep(0, 14)  
for(i in 2:15){
  clst = cutree(myhc, i) 
  rsq[i-1] = rsq.cal(mydata, clst)                               
  ### compute R^2 statistics using function
}

jpeg("R2.jpeg", height=800, width = 800, quality = 100)
plot(2:15, rsq,  type="b", xlab="k", ylab=expression(R^2))
dev.off()

### hclust plot ##################################
jpeg("city2.jpeg", height=800, width = 800, quality = 100)
fviz_dend(myhc, k=5, cex = 1,  horiz=FALSE, 
          k_colors = c("green3", "red", "blue3", "6", "grey1"), 
          color_labels_by_k=TRUE, lwd = 1,
          type = "circular",rect = TRUE,rect_lty = 1, 
          rect_fill = TRUE) 
dev.off()


jpeg("city3.jpeg", height=800, width = 800, quality = 100)
fviz_dend(myhc, k=5, cex = 1,  horiz=FALSE, 
          k_colors = c("green3", "red", "blue3", "6", "grey1"), 
          color_labels_by_k=TRUE, lwd = 1,
          type = "phylogenic",rect = TRUE,rect_lty = 1, 
          rect_fill = TRUE) 
dev.off()


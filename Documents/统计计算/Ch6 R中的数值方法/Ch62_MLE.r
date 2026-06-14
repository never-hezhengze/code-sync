## 极大似然法: mle function
set.seed(999)
y=rexp(50, rate=2)
mlogL=function(theta=1) 
{
 return(-(length(y)*log(theta)-theta*sum(y)))
}

library(stats4)
fit1=mle(mlogL)
summary(fit1)

fit2=mle(mlogL, start=list(theta=1))
summary(fit2)
    
fit3=mle(mlogL, start=list(theta=1/mean(y)))
summary(fit3)


## 一元优化法: optimize
jpeg("fig1.jpeg", height=1000, width=1000, quality = 100)
x=seq(2, 8, .001)
y=log(x+log(x))/(log(1+x))
plot(x, y, type = "l")
dev.off()
    
f=function(x)
{  
 log(x+log(x))/log(1+x)
}
optimize(f, lower=2, upper=8, maximum = TRUE)
    

## 极大似然估计: Gamma分布
m=20000
n=200
r=5
lambda=2
    
obj=function(lambda, x) 
{
 digamma(lambda*mean(x))-mean(log(x))-log(lambda)
}

est=matrix(0, m, 2)    
for (i in 1:m) 
{
 x=rgamma(n, shape=r, rate=lambda)
 u=uniroot(obj, lower=.001, upper=10e5, x=x)
 lambda.hat=u$root
 r.hat=mean(x)*lambda.hat
 est[i, ]=c(r.hat, lambda.hat)
}
    
ML=apply(est, 2, mean)
print(ML)
    
jpeg("fig2.jpeg", height=1000, width=1000, quality = 100)
hist(est[, 1], breaks="scott", freq=FALSE, xlab="r", main="")
points(ML[1], 0, cex=1.5, pch=20)
dev.off()
    
jpeg("fig3.jpeg", height=1000, width=1000, quality = 100)
hist(est[, 2], breaks="scott", freq=FALSE, xlab=bquote(lambda), main="")
points(ML[2], 0, cex=1.5, pch=20)
dev.off()
    
    
    
## Bootstrap confidence intervals
## boot and boot.ci functions in boot package
library(boot)                          
data(patch, package = "bootstrap")

theta.boot=function(dat, ind) 
{
  y=dat[ind, 1]
  z=dat[ind, 2]
  mean(y)/mean(z)
}

y=patch$y
z=patch$z
dat=cbind(y, z)
boot.obj=boot(dat, statistic=theta.boot, R=2000)

print(boot.obj)
print(boot.ci(boot.obj, type = c("basic", "norm", "perc")))
detach(package:boot)


## calculations for bootstrap confidence intervals
data(patch, package="bootstrap")
patch
n=nrow(patch)  
theta.hat=mean(patch$y)/mean(patch$z)

B=2000
theta.b=rep(0, B)
for (b in 1:B) 
{
  i=sample(1:n, size=n, replace=TRUE)
  y=patch$y[i]
  z=patch$z[i]
  theta.b[b]=mean(y)/mean(z)
}
theta.bias=mean(theta.b)-theta.hat
theta.se=sd(theta.b)

alpha=0.05
ci1.left =theta.hat-qnorm(1-alpha/2)*theta.se
ci1.right=theta.hat+qnorm(1-alpha/2)*theta.se

ci2.left =quantile(theta.b, alpha/2)
ci2.right=quantile(theta.b, 1-alpha/2)

ci3.left =2*theta.hat-quantile(theta.b, 1-alpha/2)
ci3.right=2*theta.hat-quantile(theta.b, alpha/2)

ci.result=rbind(c(ci1.left, ci1.right), c(ci2.left, ci2.right), c(ci3.left, ci3.right))
rownames(ci.result)=c("Normal", "Precentile", "Basic") 
colnames(ci.result)=c("Left", "Right")

print(list(Est=theta.hat, Bias=theta.bias, SE=theta.se))
print(round(ci.result, 4))


## Bootstrap confidence intervals 
library(boot)
data(law, package="bootstrap")
boot.obj=boot(law, R=2000, statistic=function(x,i){cor(x[i,1], x[i,2])})
print(boot.obj)
print(boot.ci(boot.obj, type=c("basic","norm","perc")))
detach(package:boot)


## Bootstrap t confidence interval
boot.t.ci=function(x, B=500, R=100, level=0.95, statistic)
{
  x=as.matrix(x)
  n=nrow(x)
  stat=rep(0, B)
  se=rep(0, B)
    
  boot.se=function(x, R, f) 
  {
    x=as.matrix(x)
    m=nrow(x)
    th=replicate(R, expr={
      i=sample(1:m, size=m, replace=TRUE)
      f(x[i, ])
      })
  return(sd(th))
  }
    
  for (b in 1:B) 
  {
    j=sample(1:n, size=n, replace=TRUE)
    y=x[j, ]
    stat[b]=statistic(y)
    se[b]=boot.se(y, R=R, f=statistic)
  }
    
  stat0=statistic(x)
  se0=sd(stat)
    
  t.stats=(stat-stat0)/se
  alpha=1-level
  Qt=quantile(t.stats, c(alpha/2, 1-alpha/2), type = 1)
  names(Qt)=rev(names(Qt))
  CI=rev(stat0-Qt*se0)
}


data(patch, package = "bootstrap")
dat=cbind(patch$y, patch$z)

stat=function(dat) 
{
  mean(dat[, 1])/mean(dat[, 2]) 
}

ci=boot.t.ci(dat, B=2000, R=200, statistic=stat)
print(ci)


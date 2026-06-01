######  Bootstrap  ###########################################
## bootstrap resampling
set.seed(999)
orig.sample=rexp(20, rate=1)
orig.sample
n=length(orig.sample)

boot.ind=sample(1:n, size=n, replace=T)
boot.ind

boot.sample=orig.sample[boot.ind]
boot.sample


## empirical functions F_n and F_n*
freq=function(m, x)
{
  a=table(x)
  b=rep(0, m)
  b[as.integer(names(a))]=a
  return(b)
}

x=c(2,2,1,1,5,4,4,3,1,2)
n=length(x)
m=max(x)
orig.prob=table(x)/n
orig.ecdf=cumsum(orig.prob)

B=200
rf=matrix(0, nrow=B, ncol=m)
for(b in 1:B)
{
  xb=sample(x, n, replace=T)
  rf[b,]=freq(m, xb)/n
}
boot.prob=apply(rf, 2, mean)
boot.ecdf=cumsum(boot.prob)

true.prob=dpois(1:5, lambda=2)
true.cdf =ppois(1:5, lambda=2)

prob.result=rbind(orig.prob, boot.prob, true.prob)
rownames(prob.result)=c("Orig", "Bootstrap", "True")
print(prob.result)

cdf.result=rbind(orig.ecdf, boot.ecdf, true.cdf)
rownames(cdf.result)=c("Orig", "Bootstrap", "True")
print(cdf.result)


## Bootstrap estimate of standard error
library(bootstrap)                    
law
tau=cor(law$LSAT, law$GPA)
print(tau)

B=200            
n=nrow(law)      
tau.boot=rep(0, B)
for (b in 1:B) 
{
  i=sample(1:n, size=n, replace=TRUE)
  LSAT=law$LSAT[i]       
  GPA=law$GPA[i]
  tau.boot[b]=cor(LSAT, GPA)
}
tau.se=sd(tau.boot)
print(tau.se)

jpeg("fig1.jpeg", height=800, width=800, quality = 100)
hist(tau.boot, prob = TRUE)
dev.off()


## boot function in boot package
library(bootstrap)                    
law

tau=function(x, i) 
{
  xi=x[i,]
  cor(xi[,1], xi[,2])
}

library(boot)                                        
obj=boot(data=law, statistic=tau, R=2000)
print(obj)

tau.se=sd(obj$t)
print(tau.se)
detach(package:boot)


## bootstrap function in bootstrap package
library(bootstrap)  
law
n=nrow(law)

tau=cor(law$LSAT, law$GPA)
print(tau)

theta=function(i, x)
{
  cor(x[i,1], x[i,2])
}

obj=bootstrap(1:n, 2000, theta, law)
print(obj)
tau.se=sd(obj$thetastar)
print(tau.se)
detach(package:bootstrap)


## Bootstrap estimate of bias
n=10
mu=0
sigma=2

x=rnorm(n, mean=mu, sd=sigma)
sigma2.hat=(n-1)*var(x)/n

B=2000   
sigma2.b=rep(0, B)
for (b in 1:B) 
{
  i=sample(1:n, size=n, replace=TRUE)
  sigma2.b[b]=(n-1)*var(x[i])/n
}
sigma2.bias=mean(sigma2.b)-sigma2.hat
print(c(sigma2.hat, sigma2.bias))


## Bootstrap estimate of bias and se
set.seed(999)
library(bootstrap)    
law
n=nrow(law)
theta.hat=cor(law$LSAT, law$GPA)

B=2000
theta.b=rep(0, B)
for (b in 1:B) 
{
  i=sample(1:n, size=n, replace=TRUE)
  LSAT=law$LSAT[i]
  GPA=law$GPA[i]
  theta.b[b]=cor(LSAT, GPA)
}
theta.bias=mean(theta.b)-theta.hat
theta.se=sd(theta.b)
print(c(theta.hat, theta.bias, theta.se))
detach(package:bootstrap)


## boot function in boot package
set.seed(999)
library(bootstrap)                    
law

tau=function(x, i) 
{
  xi=x[i,]
  cor(xi[,1], xi[,2])
}

library(boot)                                        
obj=boot(data=law, statistic=tau, R=2000)
print(obj)
detach(package:boot)
detach(package:bootstrap)


## Bootstrap estimate of bias and se
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
print(list(Est=theta.hat, Bias=theta.bias, SE=theta.se))


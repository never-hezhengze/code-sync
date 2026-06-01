## Monte Carlo Methods for Hypothesis Tests(假设检验)
##########    Empirical Type I error rate  #######################
## normal distribution with known sigma
set.seed(999)

m=1000                                
n=50                                  
alpha=0.05

mu0=0                                  
sigma=1                               

uq=qnorm(1-alpha/2)
prob=rep(0, m)
for (j in 1:m)
{
  x=rnorm(n, mean=mu0, sd=sigma)
  tobs=sqrt(n)*(mean(x)-mu0)/sigma
  prob[j]=(abs(tobs)>=uq)
}
error1=mean(prob)                   
error1.se=sqrt(error1*(1-error1)/m) 
c(error1, error1.se)



## normal distribution with unknown sigma
set.seed(999)

m=1000                                
n=50                                 
alpha=0.05

mu0=0                                  
sigma=1                               

tq=qt(1-alpha/2, df=n-1)
prob=rep(0, m)
for (j in 1:m)
{
  x=rnorm(n, mean=mu0, sd=sigma)
  tobs=sqrt(n)*(mean(x)-mu0)/sd(x)
  prob[j]=(abs(tobs)>=tq)
}
error1=mean(prob)                   
error1.se=sqrt(error1*(1-error1)/m) 
c(error1, error1.se)



## normal distribution with unknown sigma
set.seed(999)

m=1000
n=20
alpha=0.05

mu0=500
sigma=100
       
pv=rep(0, m)    
for (j in 1:m) 
{
  x=rnorm(n, mean=mu0, sd=sigma)
  ttest=t.test(x, alternative="greater", mu=mu0)
  pv[j]=ttest$p.value
}
error1=mean(pv<alpha)
error1.se=sqrt(error1*(1-error1)/m)
c(error1, error1.se)

## 上述程序设置m=100000画图
jpeg("fig2.jpeg", height=800, width=1200, quality = 100)
plot(1:m, cumsum(pv<alpha)/1:m, type="l")
abline(h=0.05)
dev.off()



## poisson distribution
m=1000                                
n=200                                  
alpha=0.05

lambda0=100                               

uq=qnorm(1-alpha/2)
prob=rep(0, m)
for (j in 1:m)
{
  x=rpois(n, lambda=lambda0)
  tobs=sqrt(n)*(mean(x)-lambda0)/sqrt(lambda0)
  prob[j]=(abs(tobs)>=uq)
}
error1=mean(prob)                   
error1.se=sqrt(error1*(1-error1)/m) 
c(error1, error1.se)



##########    Empirical Power of a test  #######################
## normal distribution with known variance
set.seed(999)

m=1000                                
n=50                                  
alpha=0.05

mu0=0 
mu=0.5
sigma=1 

uq=qnorm(1-alpha/2)

prob=rep(0, m)
for (j in 1:m)
{
  x=rnorm(n, mean=mu, sd=sigma)
  tobs=sqrt(n)*(mean(x)-mu0)/sigma
  prob[j]=(abs(tobs)>=uq)
}
power=mean(prob)                   
power.se=sqrt(power*(1-power)/m) 
c(power, power.se)



## normal distribution with unknown sigma
set.seed(999)

m=1000                                
n=50                                 
alpha=0.05

mu0=0  
mu=0.5
sigma=1                               

tq=qt(1-alpha/2, df=n-1)
prob=rep(0, m)
for (j in 1:m)
{
  x=rnorm(n, mean=mu, sd=sigma)
  tobs=sqrt(n)*(mean(x)-mu0)/sd(x)
  prob[j]=(abs(tobs)>=tq)
}
power=mean(prob)                   
power.se=sqrt(power*(1-power)/m) 
c(power, power.se)



## normal distribution with unknown sigma
set.seed(999)

m=1000
n=20
alpha=0.05

mu0=500
mu=c(seq(450, 650, 10))            #alternatives
sigma=100

M=length(mu)
power=rep(0, M)
for (i in 1:M) 
{
  mu1=mu[i]
  pv=rep(0, m)    
  for (j in 1:m) 
  {
    x=rnorm(n, mean=mu1, sd=sigma)
    ttest=t.test(x, alternative="greater", mu=mu0)
    pv[j]=ttest$p.value
  }
  power[i]=mean(pv<alpha)
}
power.se=sqrt(power*(1-power)/m)
cbind(power, power.se)

jpeg("fig3.jpeg", height=800, width=800, quality = 100)
plot(mu, power)
abline(v = mu0, lty = 1)
abline(h = 0.05, lty = 1)
dev.off()

jpeg("fig4.jpeg", height=800, width=800, quality = 100)
library(Hmisc)  #for errbar
errbar(mu, power, yplus = power+1.96*power.se, yminus = power-1.96*power.se, xlab = bquote(theta))
lines(mu, power, lty=3)
detach(package:Hmisc)
dev.off()


## poisson distribution
set.seed(999)

m=1000                                
n=200                                  
alpha=0.05

lambda0=100
lambda=seq(95, 105, 1)

uq=qnorm(1-alpha/2)

M=length(lambda)
power=rep(0, M)
for (i in 1:M) 
{
  prob=rep(0, m)
  for (j in 1:m)
  {
    x=rpois(n, lambda=lambda[i])
    tobs=sqrt(n)*(mean(x)-lambda0)/sqrt(lambda0)
    prob[j]=(abs(tobs)>=uq)
  }
  power[i]=mean(prob)   
}
power.se=sqrt(power*(1-power)/m)
cbind(power, power.se)


jpeg("fig5.jpeg", height=800, width=800, quality = 100)
plot(lambda, power)
abline(v = lambda0, lty = 1)
abline(h = alpha, lty = 1)
dev.off()



##########    power comparisons  #######################
## Kolmogorov-Smirnov test
data=rnorm(100, mean = 0, sd = 1)
ks.test(data, "pnorm", mean = 0, sd = 1)      # 检验样本是否来自标准正态分布
ks.test(data, "pnorm", mean = 0.5, sd = 1)    # 检验样本是否来自均值为0.5的正态分布

data=rexp(100, rate = 1)
ks.test(data, "pexp", rate=1)

sample1=rnorm(100, mean = 0, sd = 1)
sample2=rnorm(100, mean = 1, sd = 1)
ks.test(sample1, sample2)                        # 检验两个样本是否来自同一分布
ks.test(sample1, sample2, alternative = "less")  # 检验sample1是否随机小于sample2

data=rnorm(100, mean = 0, sd =1)
ks.test(data, "pnorm")
data=rnorm(100, mean = 0, sd =2)
ks.test(data, "pnorm", exact = T)
ks.test(data, "pnorm", mean = 0, sd = 2, exact = T)  


## Lilliefors test
library(nortest)
data=rnorm(100, mean = 0, sd = 2)
lillie.test(data)

data=runif(100, 0, 1)
lillie.test(data)
detach(package:nortest)


## Shapiro-Wilk test
data=rnorm(30, mean = 0, sd = 1)
shapiro.test(data)

data=rexp(30, rate = 1)
shapiro.test(data)

## Anderson-Darling test
library(nortest)
data=rnorm(30, mean = 0, sd = 1)
ad.test(data)

data=rexp(30, rate = 1)
ad.test(data)
detach(package:nortest)

## energy test
library(energy)
data=matrix(rnorm(200), ncol=2) 
mvnorm.etest(data, R = 999)

data=cbind(rnorm(100), rexp(100), runif(100, -1, 1))
mvnorm.etest(data, R = 999)
detach(package:energy)


## power comparisons
library(nortest)
library(energy)

m=1000                                
n=30                                  
alpha=0.05

test1=test2=test3=test4=test5=rep(0, m)
result=matrix(0, 11, 6)
for (i in 0:10) 
{
  epsilon=i*0.1
  for (j in 1:m) 
    {
    sigma=sample(c(1, 10), replace=TRUE, size=n, prob=c(1-epsilon, epsilon))
    x=rnorm(n, 0, sigma)

    test1[j]=as.integer(ks.test(x, "pnorm", exact=T)$p.value<alpha)
    test2[j]=as.integer(lillie.test(x)$p.value<alpha)
    test3[j]=as.integer(shapiro.test(x)$p.value<alpha)
    test4[j]=as.integer(ad.test(x)$p.value<alpha)
    test5[j]=as.integer(mvnorm.etest(x, R=200)$p.value<alpha)
  }
  result[i+1, ]=c(epsilon, mean(test1), mean(test2), mean(test3), mean(test4), mean(test5))
  print(result[i+1, ])
}
colnames(result)=c("epsilon", "KS", "Lillie", "SW", "AD", "Energy")
print(result)

detach(package:nortest)
detach(package:energy)


# plot the empirical estimates of power
jpeg("fig6.jpeg", height=800, width=800, quality = 100)
plot(result[,1], result[,2], ylim = c(0, 1), type = "l",xlab = bquote(epsilon), ylab = "power")
lines(result[,1], result[,3], lty = 2, col="red")
lines(result[,1], result[,4], lty = 3, col="blue")
lines(result[,1], result[,5], lty = 4, col="pink")
lines(result[,1], result[,6], lty = 5, col="green")
abline(h = alpha, lty = 3)
legend("topright", 1, c("KS", "Lillie", "SW", "AD", "Energy"), 
       lty = 1:5, col=c("black","red", "blue", "pink", "green"), inset = 0.05)
dev.off()


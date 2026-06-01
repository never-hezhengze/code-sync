### Monte Carlo methods for Confidence Level(区间估计)
## confidence interval of normal distribution 
## mu with sigma is known
set.seed(999)

m=1000                                ## 模拟次数
n=50                                  ## 样本量
alpha=0.05                            ## 置信水平为1-alpha
mu=0                                  ## 均值真值
sigma=1                               ## 标准差真值

uq=qnorm(1-alpha/2)

ci1=matrix(0, nrow=m, ncol=2)
prob1=rep(0, m)
for (j in 1:m)
{
  x=rnorm(n, mean=mu, sd=sigma)
  barx=mean(x)
  
  ci1[j, 1]=barx-uq*sigma/sqrt(n)
  ci1[j, 2]=barx+uq*sigma/sqrt(n)
  prob1[j]=(mu>=ci1[j, 1]&mu<=ci1[j, 2])
}

prob.est=mean(prob1)                   ## 覆盖率
inter.est=mean(ci1[, 2]-ci1[, 1])      ## 平均长度
c(prob.est, inter.est)


## mu with sigma is unknown
set.seed(999)

m=1000                                 ## 模拟次数
n=50                                   ## 样本量
alpha=0.05                             ## 置信水平为1-alpha
mu=0                                   ## 均值真值
sigma=1                                ## 标准差真值

tq=qt(1-alpha/2, df=n-1)

ci2=matrix(0, nrow=m, ncol=2)
prob2=rep(0, m)
for (j in 1:m)
{
  x=rnorm(n, mean=mu, sd=sigma)
  barx=mean(x)
  sx=sd(x)
  
  ci2[j, 1]=barx-tq*sx/sqrt(n)
  ci2[j, 2]=barx+tq*sx/sqrt(n)
  prob2[j]=(mu>=ci2[j, 1]&mu<=ci2[j, 2])
}

prob.est=mean(prob2)                   ## 覆盖率
inter.est=mean(ci2[, 2]-ci2[, 1])      ## 平均长度
c(prob.est, inter.est)


## sigma^2
set.seed(999)

m=1000                               
n=50                                
alpha=0.05                             
mu=0                                  
sigma=1                              

cq1=qchisq(1-alpha/2, df=n-1)
cq2=qchisq(alpha/2, df=n-1)

ci=matrix(0, nrow=m, ncol=2)
prob=rep(0, m)
for (j in 1:m)
{
  x=rnorm(n, mean=mu, sd=sigma)
  barx=mean(x)
  s2x=var(x)
  
  ci[j, 1]=(n-1)*s2x/cq1
  ci[j, 2]=(n-1)*s2x/cq2
  prob[j]=(sigma^2>=ci[j, 1]&sigma^2<=ci[j, 2])
}

prob.est=mean(prob)                   
inter.est=mean(ci[, 2]-ci[, 1])      
c(prob.est, inter.est)


## plot the confidence level curve
## 上述程序设置m=100000
jpeg("fig1.jpeg", height=800, width=1200, quality = 100)
cov.rate<-cumsum(prob)/1:m
plot(2:m, cov.rate[-1], type="l")
abline(h=0.95)
dev.off()


## confidence interval of proportion
m=1000
n=50
alpha=0.05
p=0.2

uq=qnorm(1-alpha/2)

ci=matrix(0, nrow=m, ncol=2)
prob=rep(0, m)
for (j in 1:m)
{
  x=rbinom(n, size=1, prob=p)
  barx=mean(x)
  sx=sqrt(barx*(1-barx)/n)
  
  ci[j, 1]=barx-uq*sx
  ci[j, 2]=barx+uq*sx
  prob[j]=(p>=ci[j, 1]&p<=ci[j, 2])
}

prob.est=mean(prob)
inter.est=mean(ci[, 2]-ci[, 1])
c(prob.est, inter.est)



## confidence interval of two normal distributions
## mu1-mu2 with equal variances
m=1000                                 
n1=50 
n2=50  
alpha=0.05     

mu1=0
mu2=0.2
sigma1=1
sigma2=1                         

tq=qt(1-alpha/2, df=n1+n2-2)

ci=matrix(0, nrow=m, ncol=2)
prob=rep(0, m)
for (j in 1:m)
{
  x=rnorm(n1, mean=mu1, sd=sigma1)
  y=rnorm(n2, mean=mu2, sd=sigma2)
  
  barx=mean(x)
  s2x=var(x)
  bary=mean(y)
  s2y=var(y)
  s2w=((n1-1)*s2x+(n2-1)*s2y)/(n1+n2-2)
  
  ci[j, 1]=(barx-bary)-tq*sqrt(s2w*(1/n1+1/n2))
  ci[j, 2]=(barx-bary)+tq*sqrt(s2w*(1/n1+1/n2))
  prob[j]=((mu1-mu2)>=ci[j, 1]&(mu1-mu2)<=ci[j, 2])
}

prob.est=mean(prob)                   
inter.est=mean(ci[, 2]-ci[, 1])      
c(prob.est, inter.est)


## mu1-mu2 with unequal variances
m=1000                                 
n1=100 
n2=100
alpha=0.05     

mu1=0
mu2=0.2
sigma1=1
sigma2=3                         

uq=qnorm(1-alpha/2)

ci=matrix(0, nrow=m, ncol=2)
prob=rep(0, m)
for (j in 1:m)
{
  x=rnorm(n1, mean=mu1, sd=sigma1)
  y=rnorm(n2, mean=mu2, sd=sigma2)
  
  barx=mean(x)
  s2x=var(x)
  bary=mean(y)
  s2y=var(y)

  ci[j, 1]=(barx-bary)-uq*sqrt(s2x/n1+s2y/n2)
  ci[j, 2]=(barx-bary)+uq*sqrt(s2x/n1+s2y/n2)
  prob[j]=((mu1-mu2)>=ci[j, 1]&(mu1-mu2)<=ci[j, 2])
}

prob.est=mean(prob)                   
inter.est=mean(ci[, 2]-ci[, 1])      
c(prob.est, inter.est)


## sigma1^2/sigma2^2
m=1000                                 
n1=50 
n2=50
alpha=0.05     

mu1=0
mu2=0.2
sigma1=1
sigma2=2                         

fq1=qf(1-alpha/2, df1=n1-1, df2=n2-1)
fq2=qf(alpha/2, df1=n1-1, df2=n2-1)

ci=matrix(0, nrow=m, ncol=2)
prob=rep(0, m)
for (j in 1:m)
{
  x=rnorm(n1, mean=mu1, sd=sigma1)
  y=rnorm(n2, mean=mu2, sd=sigma2)
  s2x=var(x)
  s2y=var(y)
  
  ci[j, 1]=(s2x/s2y)/fq1
  ci[j, 2]=(s2x/s2y)/fq2
  prob[j]=((sigma1^2/sigma2^2)>=ci[j, 1]&(sigma1^2/sigma2^2)<=ci[j, 2])
}

prob.est=mean(prob)                   
inter.est=mean(ci[, 2]-ci[, 1])      
c(prob.est, inter.est)


## confidence interval of two proportions 
m=1000
n1=200
n2=300
alpha=0.05

p1=0.2
p2=0.5

uq=qnorm(1-alpha/2)

ci=matrix(0, nrow=m, ncol=2)
prob=rep(0, m)
for (j in 1:m)
{
  x=rbinom(n1, size=1, prob=p1)
  y=rbinom(n2, size=1, prob=p2)
  
  barx=mean(x)
  s2x=barx*(1-barx)/n1
  bary=mean(y)
  s2y=bary*(1-bary)/n2
  
  ci[j, 1]=(barx-bary)-uq*sqrt(s2x+s2y)
  ci[j, 2]=(barx-bary)+uq*sqrt(s2x+s2y)
  prob[j]=((p1-p2)>=ci[j, 1]&(p1-p2)<=ci[j, 2])
}

prob.est=mean(prob)
inter.est=mean(ci[, 2]-ci[, 1])
c(prob.est, inter.est)


## Monte Carlo estimation of expectation and variance
mu=0
sigma=1
m=1000
n=500
barx=rep(0, m)
for (j in 1:m)
{
  x=rnorm(n, mean=mu, sd=sigma)
  barx[j]=mean(x)
}
c(mean(barx), mu)
c(var(barx), sigma^2/n)


### Monte Carlo estimation and its standard error
m=1000
g=rep(0, m)
for (j in 1:m) 
{
  x=rnorm(2)
  g[j]=abs(x[1] - x[2])
}
est=mean(g)
est.var=var(g)/m
est.se=sd(g)/sqrt(m)    
c(est, est.var, est.se)


### Monte Carlo estimation of MSE
## trimmed mean
m=1000
n=20
tmean=rep(0, m)
for (j in 1:m) 
{
  x=sort(rnorm(n))
  tmean[j]=mean(x[2:(n-1)])
}
mse.est=mean(tmean^2)
mse.se=sd(tmean^2)/sqrt(m)  
c(mse.est, mse.se)


## median
m=1000
n=20
tmean=rep(0, m)
for (j in 1:m) 
{
  x=sort(rnorm(n))
  tmean[j]=median(x)
}
mse.est=mean(tmean^2)
mse.se=sd(tmean^2)/sqrt(m)  
c(mse.est, mse.se)


## k-level trimmed mean
trimmed.mse=function(m, n, k, p) 
{
  tmean=rep(0, m)
  for (j in 1:m) 
  {
    sigma=sample(c(1, 10), size = n, replace = TRUE, prob = c(p, 1-p))
    x=sort(rnorm(n, 0, sigma))
    tmean[j]=mean(x[(k+1):(n-k)])
  }
  mse.est=mean(tmean^2)
  mse.se=sd(tmean^2)/sqrt(m) 
  return(c(mse.est, mse.se))
}

m=1000
n=20         
K=n/2-1
mse=matrix(0, n/2, 6)
for (k in 0:K) 
{
  mse[k+1, 1:2]=trimmed.mse(m=m, n=n, k=k, p=1.0)
  mse[k+1, 3:4]=trimmed.mse(m=m, n=n, k=k, p=0.95)
  mse[k+1, 5:6]=trimmed.mse(m=m, n=n, k=k, p=0.9)
}
round(mse,3)


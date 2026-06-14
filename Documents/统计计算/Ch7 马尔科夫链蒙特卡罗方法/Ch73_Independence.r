## Independence方法
# setups
set.seed(999)
p=0.2           
n=50            
mu=c(0, 5)      
sigma=c(1, 1)

# generate the observed sample
i=sample(1:2, size=n, replace=TRUE, prob=c(p, 1-p))
x=rnorm(n, mu[i], sigma[i])

# hist of sample x and true density
jpeg("fig11.jpeg", height=800, width=800, quality = 100)
hist(x, ylim=c(0, 0.4), freq=F)
z=seq(min(x), max(x), length=100)
lines(z, p*dnorm(z,mean=mu[1],sd=sigma[1])+(1-p)*dnorm(z,mean=mu[2],sd=sigma[2]))
dev.off()

# generate markov chain
m=10000 
xt=rep(0, m)
a=1             
b=1             
xt[1]=rbeta(1, a, b)
y=rbeta(m, a, b)
u=runif(m)
for (i in 2:m) 
{
  fy=y[i]*dnorm(x, mu[1], sigma[1])+(1-y[i])*dnorm(x, mu[2], sigma[2])
  fx=xt[i-1]*dnorm(x, mu[1], sigma[1])+(1-xt[i-1])*dnorm(x, mu[2], sigma[2])
  r=prod(fy/fx)*(xt[i-1]^(a-1)*(1-xt[i-1])^(b-1))/(y[i]^(a-1)*(1-y[i])^(b-1))
  
  if (u[i]<=r) 
  {xt[i]=y[i]} 
  else
  {xt[i]=xt[i-1]}
}

index=(0.2*m+1):m 
p.est=mean(xt[index])
print(p.est)


# hist plot
jpeg("fig12.jpeg", height=800, width=1600, quality = 100)
hist(xt[(0.2*m+1):m], main="", xlab="p", prob=TRUE)
dev.off()


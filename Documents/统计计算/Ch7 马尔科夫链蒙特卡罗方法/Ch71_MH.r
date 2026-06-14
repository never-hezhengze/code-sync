## Metropolis-Hastings方法
f=function(x, sigma) 
{
  stopifnot(sigma>0)
  if(any(x<0)) return(0)
  return((x/sigma^2)*exp(-x^2/(2*sigma^2)))
}

set.seed(111)
m=10000
sigma=4
x=rep(0, m)
x[1]=rchisq(1, df=1)
k=0
u=runif(m)
for (i in 2:m) 
{
  xt=x[i-1]
  y=rchisq(1, df=xt)
  num=f(y, sigma)*dchisq(xt, df=y)
  den=f(xt, sigma)*dchisq(y, df=xt)
  
  if (u[i]<=num/den) 
  {
    x[i]=y
  }
  else 
  {
    x[i]=xt
    k=k+1     
  }
}
print(k)
print(k/m)

## full chain
index=1:m      
jpeg("fig1.jpeg", height=1000, width=6000, quality = 100)
plot(index, x[index], type="l", main="", ylab="x")
dev.off()

## burn-in  
index=(0.2*m+1):m        
jpeg("fig2.jpeg", height=1000, width=6000, quality = 100)
plot(index, x[index], type="l", main="", ylab="x")
dev.off()

## tail
index=(0.9*m+1):m       
jpeg("fig3.jpeg", height=1000, width=6000, quality = 100)
plot(index, x[index], type="l", main="", ylab="x")
dev.off()


## Rayleigh quantiles and QQ plot
index=(0.2*m+1):m                             
y=x[index]   

a=seq(from=0.005, to=0.995, by=0.01)
QR=sigma*sqrt(-2*log(1-a))  
QM=quantile(y, a)
print(cbind(QR, QM))

jpeg("fig4.jpeg", height=800, width=800, quality = 100)
hist(y, breaks="scott", main="", xlab="", freq=FALSE)
lines(QR, f(QR, sigma=4))
dev.off()

jpeg("fig5.jpeg", height=800, width=800, quality = 100)
qqplot(QR, QM, main="", xlab="Rayleigh Quantiles", ylab="Sample Quantiles")
lines(QR, QR)
dev.off()



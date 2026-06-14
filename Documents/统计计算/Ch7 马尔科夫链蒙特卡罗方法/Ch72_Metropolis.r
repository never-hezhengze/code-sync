## Metropolis方法
f=function(x) 
{
  return(1/(pi*(1+x^2)))
}

set.seed(111)
m=10000
b=10
x=rep(0, m)
x[1]=rnorm(1, mean=0, sd=b)
k=0
u=runif(m)
for (i in 2:m) 
{
  xt=x[i-1]
  y=rnorm(1, mean=xt, sd=b)
  num=f(y)
  den=f(xt)
  
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
jpeg("fig6.jpeg", height=1000, width=6000, quality = 100)
plot(index, x[index], type="l", main="", ylab="x")
dev.off()

## burn-in  
index=(0.4*m+1):m        
jpeg("fig7.jpeg", height=1000, width=6000, quality = 100)
plot(index, x[index], type="l", main="", ylab="x")
dev.off()

## tail
index=(0.9*m+1):m       
jpeg("fig8.jpeg", height=1000, width=6000, quality = 100)
plot(index, x[index], type="l", main="", ylab="x")
dev.off()


## Rayleigh quantiles and QQ plot
index=(0.4*m+1):m                             
y=x[index]   

a=seq(from=0.005, to=0.995, by=0.01)
QR=qcauchy(a) 
QM=quantile(y, a)
print(cbind(QR, QM))

jpeg("fig9.jpeg", height=800, width=800, quality = 100)
hist(y, breaks="scott", main="", xlab="", freq=FALSE)
lines(QR, dcauchy(QR))
dev.off()

jpeg("fig10.jpeg", height=800, width=800, quality = 100)
qqplot(QR, QM, main="", xlab="Rayleigh Quantiles", ylab="Sample Quantiles")
lines(QR, QR)
dev.off()



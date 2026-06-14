## 二分法
a=0.5
n=20
y1=-a/(n-1)+sqrt((a/(n-1))^2-a^2+n-2)
y2=-a/(n-1)-sqrt((a/(n-1))^2-a^2+n-2)

bisection=function(b0, b1, eps=.Machine$double.eps^0.25, iter.max=1000)
{
  f=function(y, a, n) 
  {
    y^2+2*a*y/(n-1)+a^2-n+2
  }
  
  r=seq(b0, b1, length=3)
  y=c(f(r[1], a, n), f(r[2], a, n), f(r[3], a, n))
  
  if (y[1]*y[3]>0)
    stop("f does not have opposite sign at endpoints")
  
  it=0
  while(it<iter.max & abs(y[2])>eps) 
  {
    it=it+1
    
    if (y[1]*y[2]<0) 
    {
      r[3]=r[2]
      y[3]=y[2]
    } 
    else 
    {
      r[1]=r[2]
      y[1]=y[2]
    }
    
    r[2]=(r[1]+r[3])/2
    y[2]=f(r[2], a, n)
    cat(it, c(r[1], r[2], r[3], y[1], y[2], y[3]),"\n")
  }
  return(list(root=r[2], f.root=y[2], iter=it))
}

result1=bisection(0, 5*n)
print(result1)

result2=bisection(-5*n, 0)
print(result2)

result=matrix(c(y1, y2, result1$root, result2$root), nrow=2, byrow = T)
print(result)


## Brent法: uniroot, polyroot
a=0.5
n=20

out1=uniroot(function(y){y^2+2*a*y/(n-1)+a^2-n+2}, lower=0, upper=n*5)
unlist(out1)

out2=uniroot(function(y){y^2+2*a*y/(n-1)+a^2-n+2}, interval=c(-n*5, 0))
unlist(out2)

out3=polyroot(c(a^2-(n-2), 2*a/(n-1), 1))
print(out3)


## Newton法
a=0.5
n=20

nt=function(b0, eps=.Machine$double.eps^0.25, iter.max=1000)
{
  f=function(y, a, n) 
  {
    y^2+2*a*y/(n-1)+a^2-n+2
  }
  
  fd=function(y,a,n)
  {
    2*y+2*a/(n-1)
  }
  
  b1=b0
  b0=b0-1
  it=0
  while(it<iter.max & abs(b1-b0)>eps)
  {
    it=it+1
    b0=b1
    b1=b0-f(b0,a,n)/fd(b0,a,n)
    cat(it, c(b0, b1, abs(b1-b0)), "\n")
  }
  return(list(root=b1, iter=it))
}

result1=nt(0)
print(result1)

result2=nt(-1)
print(result2)


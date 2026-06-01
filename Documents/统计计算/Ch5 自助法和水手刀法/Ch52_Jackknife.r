########   The Jackknife  ####################################

## Jackknife estimate of bias
data(patch, package="bootstrap")
patch
n=nrow(patch)

y=patch$y
z=patch$z
theta.hat=mean(y)/mean(z)

theta.jack=rep(0, n)
for (i in 1:n)
{
  theta.jack[i]=mean(y[-i])/mean(z[-i])
}
  
theta.bias=(n-1)*(mean(theta.jack)-theta.hat)
print(c(theta.hat, theta.bias))


## Jackknife estimate of standard error
data(patch, package="bootstrap")
patch
n=nrow(patch)

y=patch$y
z=patch$z
theta.hat=mean(y)/mean(z)

theta.jack=rep(0, n)
for (i in 1:n)
{
  theta.jack[i]=mean(y[-i])/mean(z[-i])
}
theta.bias=(n-1)*(mean(theta.jack)-theta.hat)
theta.se=((n-1)/sqrt(n))*sd(theta.jack)
print(c(theta.hat, theta.bias, theta.se))


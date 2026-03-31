### Example (Transformation Method, Logarithmic, version 2)
n = 1000
theta = 0.5
u = runif(n)  
v = runif(n)
x = floor(1 + log(v) / log(1 - (1 - theta)^u))
    
k = 1:max(x)  
p = -1 / log(1 - theta) * theta^k / k
se = sqrt(p*(1-p)/n)
p.hat = tabulate(x)/n
print(round(rbind(p.hat, p, se), 3))

## Logarithmic, version 2
rlogarithmic2 = function(n, theta) 
{
  stopifnot(all(theta > 0 & theta < 1))
  th = rep(theta, length=n)
  u = runif(n)
  v = runif(n)
  x = floor(1 + log(v) / log(1 - (1 - th)^u))
  return(x)
}

rlogarithmic2(1000, 0.5) 


### Example  (Sums, Chisquare)
n = 1000
nu = 2
X = matrix(rnorm(n*nu), n, nu)^2 
#method 1
y = rowSums(X)
#method 2
y = apply(X, 1, sum)  
y
    

### Example   (Mixture, several gamma)
n = 5000
k = sample(1:5, size=n, replace=TRUE, prob=(1:5)/15)
rate = 1/k
x = rgamma(n, shape=3, rate=rate)
    
#plot the density of the mixture
jpeg("fig2.jpeg", height=800, width=800, quality = 100)
plot(density(x), xlim=c(0,40), ylim=c(0,.3), lwd=3, xlab="x", main="")
for (i in 1:5) lines(density(rgamma(n, 3, 1/i)))    
dev.off()


### Example   (Mixture, plot density of mixture)
f = function(x, lambda, theta) 
{
  fx = sum(dgamma(x, 3, lambda) * theta)  #density of the mixture at the point x
  return(fx)
}
    
p = c(.1,.2,.2,.3,.2)
lambda = c(1,1.5,2,2.5,3)
    
x = seq(0, 8, length=200)
dim(x) = length(x)                         #need for apply
y = apply(x, 1, f, lambda=lambda, theta=p) #compute density of the mixture f(x) along x
 
#plot the density of the mixture
jpeg("fig3.jpeg", height=800, width=800, quality = 100)
plot(x, y, type="l", ylim=c(0,.85), lwd=3, ylab="Density")
    
for (j in 1:5) 
{
  #add the j-th gamma density to the plot
  y = apply(x, 1, dgamma, shape=3, rate=lambda[j])
  lines(x, y)
}
dev.off()
    

    
### simple Monte Carlo integration 

###  simple Monte Carlo integration, \int_{0}^{1}g(x)dx
m = 10000
x = runif(m)
theta.hat = mean(exp(-x))
print(theta.hat)
print(1 - exp(-1))


###  simple Monte Carlo integration, \int_{a}^{b}g(x)dx
m = 10000
x = runif(m, min=2, max=4)
theta.hat = mean(exp(-x)) * 2
print(theta.hat)
print(exp(-2) - exp(-4))


###  simple Monte Carlo integration, \int_{a}^{b}g(x)dx
#source("MCint.r")
#theta.hat = MC.int.simple(a=0, b=1)
#print(theta.hat)

#theta.hat = MC.int.simple(a=2, b=4)
#print(theta.hat)


###  simple Monte Carlo integration, cdf of normal
x = seq(0.1, 2.5, length = 10)
#x = seq(0.01, 3, by = 0.01)

m = 10000
u = runif(m)

cdf = numeric(length(x))
for (i in 1:length(x)) 
{
  g = x[i] * exp(-(x[i] * u)^2 / 2)
  cdf[i] = mean(g) / sqrt(2 * pi) + 0.5
}

Phi = pnorm(x)
print(round(rbind(x, cdf, Phi), 3))


###  Monte Carlo integration, cdf of normal, hit or miss
x = seq(.1, 2.5, length = 10)
#x = seq(0.01, 3, by = 0.01)

m = 10000
z = rnorm(m)

dim(x) = length(x)
cdf = apply(x, MARGIN = 1, FUN = function(x, z) {mean(z < x)}, z = z)

Phi = pnorm(x)
print(round(rbind(x, cdf, Phi), 3))


### Monte Carlo integration, variance 
x = 2
m = 10000

## hit-or-miss method
z = rnorm(m)
g = (z < x)  

## integration and variance
cdf = mean(g)
cdf.var = var(g)/ m
#cdf.var = mean((g - mean(g))^2) / m

c(cdf, cdf.var)
alpha = 0.05
c(cdf-qnorm(1-alpha/2)*sqrt(cdf.var), cdf+qnorm(1-alpha/2)*sqrt(cdf.var))


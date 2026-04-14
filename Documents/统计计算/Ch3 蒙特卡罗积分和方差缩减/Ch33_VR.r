### Variance reduction, antithetic method, normal
MC.Phi = function(x, R = 10000, antithetic = TRUE) 
{
  u = runif(R/2)
  if (!antithetic)             ## antithetic= F, simple MC
  {v = runif(R/2)}
  else                         ## default, antithetic method
  {v = 1 - u}
  u = c(u, v)
  
  cdf = numeric(length(x))
  for (i in 1:length(x)) 
  {
    g = x[i] * exp(-(u * x[i])^2 / 2)
    cdf[i] = mean(g) / sqrt(2 * pi) + 0.5
  }
  cdf
}

x = seq(0.1, 2.5, length=5)
Phi = pnorm(x)

set.seed(123)
MC1 = MC.Phi(x, antithetic = FALSE)

set.seed(123)
MC2 = MC.Phi(x)

print(round(rbind(x, MC1, MC2, Phi), 5))


m = 1000
x = 1.95

MC1 = MC2 = numeric(m)
for (i in 1:m) 
{
  MC1[i] = MC.Phi(x, R = m, antithetic = FALSE)
  MC2[i] = MC.Phi(x, R = m)
}

print(sd(MC1))
print(sd(MC2))
print((var(MC1)-var(MC2))/var(MC1))


### Variance reduction, control variate method
m = 10000
a = -12+6*(exp(1)-1)

U = runif(m)
T1 = exp(U)                  #simple MC
T2 = exp(U)+a*(U - 1/2)      #controlled MC

MC1 = mean(T1)
MC1
Var1 = var(T1)/m
Var1

MC2 = mean(T2)
MC2
Var2 = var(T2)/m
Var2

(Var1-Var2)/Var1


### Variance reduction, control variate method
g = function(u)
{
  exp(-u)/(1+u^2) 
}


f = function(u)
{
  exp(-0.5)/(1+u^2)
}
  

#est of c*
u = runif(10000)
B = f(u)
A = g(u)

cor(A, B)
a = -cov(A,B) / var(B)   
a

#integration
m = 100000
u = runif(m)
T1 = g(u)
T2 = T1 + a * (f(u) - exp(-0.5)*pi/4)

MC1 = mean(T1)
MC1
Var1 = var(T1)/m
Var1

MC2 = mean(T2)
MC2
Var2 = var(T2)/m
Var2

(Var1-Var2)/Var1


### Importance sampling 
## plots
x = seq(0, 1, 0.01)
f0 = rep(1, length(x))
f1 = exp(-x)
f2 = (1 / pi) / (1 + x^2)
f3 = exp(-x) / (1 - exp(-1))
f4 = 4 / ((1 + x^2) * pi)
g = exp(-x) / (1 + x^2)


jpeg("fig3.jpeg", height=800, width=1600, quality = 100)
par(mfrow=c(1,2))
plot(x, g, type = "l", main = "Importance sampling function f0,...f4 with g", 
     ylab = "", ylim = c(0,2), lwd = 2,col=1)
lines(x, f0, lty = 2, lwd = 2, col=2)
lines(x, f1, lty = 3, lwd = 2, col=3)
lines(x, f2, lty = 4, lwd = 2, col=4)
lines(x, f3, lty = 5, lwd = 2, col=5)
lines(x, f4, lty = 6, lwd = 2, col=6)
legend("topright", legend = c("g", paste("f",0:4,sep="")),
       lty = 1:6, col=1:6, lwd = 2, inset = 0.02)

plot(x, g, type = "l", main = "Ratios of g/f", ylab = "",
     ylim = c(0,3.2), lwd = 2, lty = 2, col=2)
lines(x, g/f1, lty = 3, lwd = 2, col=3)
lines(x, g/f2, lty = 4, lwd = 2, col=4)
lines(x, g/f3, lty = 5, lwd = 2, col=5)
lines(x, g/f4, lty = 6, lwd = 2, col=6)
legend("topright", legend =paste("g/",paste("f",0:4,sep=""),sep=""),
       lty = 2:6, col=2:6, lwd = 2, inset = 0.02)
dev.off()


## importance sampling
m = 10000
theta.hat = se = numeric(5)

g = function(x) 
{
  exp(-x - log(1+x^2)) * (x > 0) * (x < 1)
}

x = runif(m)     #using f0
fg = g(x)
theta.hat[1] = mean(fg)
se[1] = sd(fg)

x = rexp(m, 1)   #using f1
fg = g(x) / exp(-x)
theta.hat[2] = mean(fg)
se[2] = sd(fg)

x = rcauchy(m)   #using f2
i = c(which(x > 1), which(x < 0))
x[i] = 2 
fg = g(x) / dcauchy(x)
theta.hat[3] = mean(fg)
se[3] = sd(fg)

u = runif(m)     #f3, inverse transform method
x = - log(1 - u * (1 - exp(-1)))
fg = g(x) / (exp(-x) / (1 - exp(-1)))
theta.hat[4] = mean(fg)
se[4] = sd(fg)

u = runif(m)    #f4, inverse transform method
x = tan(pi * u / 4)
fg = g(x) / (4 / ((1 + x^2) * pi))
theta.hat[5] = mean(fg)
se[5] = sd(fg)

rbind(theta.hat, se)


### stratified sampling
M = 10000  #number of replicates
k = 10     #number of strata
r = M / k  #replicates per stratum
N = 50     #number of times to repeat the estimation
T2 = numeric(k)
estimates = matrix(0, N, 2)

g = function(x) 
{
  exp(-x - log(1+x^2)) * (x > 0) * (x < 1)
}

for (i in 1:N) 
{
  estimates[i, 1] = mean(g(runif(M)))
  for (j in 1:k)
    T2[j] = mean(g(runif(M/k, (j-1)/k, j/k)))
  estimates[i, 2] = mean(T2)
}

apply(estimates, 2, mean)
apply(estimates, 2, var)


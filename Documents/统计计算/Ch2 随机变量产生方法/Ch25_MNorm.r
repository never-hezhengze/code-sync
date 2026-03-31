### Example   (Multivariate normal, Spectral decomposition method)
rmvn.eigen = function(n, mu, Sigma) 
{
    # generate n random vectors from MVN(mu, Sigma) by spectral decomposition
    d = length(mu)                                 ## dimension
    ev = eigen(Sigma, symmetric = TRUE)            ## spectral decomposition
    lambda = ev$values                            
    V = ev$vectors                                
    R = V %*% diag(sqrt(lambda)) %*% t(V)
        
    Z = matrix(rnorm(n*d), nrow = n, ncol = d)
    X = Z %*% R + matrix(mu, n, d, byrow = TRUE)
    X
}

# generate the sample
# mean and covariance parameters
n = 1000
mu = c(0, 0)
Sigma = matrix(c(1, 0.9, 0.9, 1), nrow = 2, ncol = 2)
    
X = rmvn.eigen(n, mu, Sigma)
print(apply(X, 2, mean))
print(cor(X))
    
jpeg("fig4.jpeg", height=800, width=800, quality = 100)
plot(X, xlab = "x", ylab = "y", pch = 20)
dev.off()


### Example   (Multivariate normal, SVD method)
rmvn.svd = function(n, mu, Sigma) 
{
    # generate n random vectors from MVN(mu, Sigma) by SVD
    d = length(mu)
    S = svd(Sigma)                                 ## SVD
    R = S$u %*% diag(sqrt(S$d)) %*% t(S$v) 
        
    Z = matrix(rnorm(n*d), nrow=n, ncol=d)
    X = Z %*% R + matrix(mu, n, d, byrow=TRUE)
    X
}

# generate the sample
# mean and covariance parameters
n = 1000
mu = c(0, 0)
Sigma = matrix(c(1, 0.9, 0.9, 1), nrow = 2, ncol = 2)
    
X = rmvn.svd(n, mu, Sigma)
print(apply(X, 2, mean))
print(cor(X))
    
jpeg("fig5.jpeg", height=800, width=800, quality = 100)
plot(X, xlab = "x", ylab = "y", pch = 20)
dev.off()
 

### Example  (Multivariate normal, Choleski factorization method)
rmvn.Choleski = function(n, mu, Sigma) 
{
    # generate n random vectors from MVN(mu, Sigma) by Choleski
    d = length(mu)
    Q = chol(Sigma)                              # Choleski factorization
        
    Z = matrix(rnorm(n*d), nrow=n, ncol=d)
    X = Z %*% Q + matrix(mu, n, d, byrow=TRUE)
    X
}
    
#generating the samples according to the mean and covariance
#structure as the four-dimensional iris virginica data
y = subset(x=iris, Species=="virginica")[, 1:4]
mu = apply(y, 2, mean)
Sigma = cov(y)
mu
Sigma

#now generate MVN data with this mean and covariance
X = rmvn.Choleski(200, mu, Sigma)
    
jpeg("fig6.jpeg", height=800, width=800, quality = 100)
pairs(X)
dev.off()
    

### Example    (Multivariate normal, Comparing performance of MVN generators)
library(MASS)
library(mvtnorm)
n = 100          #sample size
d = 30           #dimension
N = 2000         #iterations
    
set.seed(10)
mu = numeric(d)                           ## mean
Sigma = cov(matrix(rnorm(n*d), n, d))     ## variance

set.seed(100)
system.time(for (i in 1:N) rmvn.eigen(n, mu, Sigma))
    
set.seed(100)
system.time(for (i in 1:N) rmvn.svd(n, mu, Sigma))
    
set.seed(100)
system.time(for (i in 1:N) rmvn.Choleski(n, mu, Sigma))
    
set.seed(100)
system.time(for (i in 1:N) mvrnorm(n, mu, Sigma))                 ## need package MASS
    
set.seed(100)
system.time(for (i in 1:N) rmvnorm(n, mu, Sigma, method="eigen")) ## need package mvtnorm
    
set.seed(100)
system.time(for (i in 1:N) rmvnorm(n, mu, Sigma, method="svd"))   ## need package mvtnorm
    
set.seed(100)
system.time(for (i in 1:N) rmvnorm(n, mu, Sigma, method="chol"))  ## need package mvtnorm
    
detach(package:MASS)
detach(package:mvtnorm)
    

### Example  (Multivariate normal, Multivariate normal mixture)
library(MASS)  
    
loc.mix.0 = function(n, p, mu1, mu2, Sigma) 
{
    #generate sample from BVN location mixture
    X = matrix(0, n, length(mu1))

    for (i in 1:n) 
    {
        k = rbinom(1, size = 1, prob = p)
        if (k)
            {X[i,] = mvrnorm(1, mu = mu1, Sigma)} 
        else
            {X[i,] = mvrnorm(1, mu = mu2, Sigma)}
    }
    return(X)
}

x = loc.mix.0(10000, 0.5, rep(0, 4), 2:5, Sigma = diag(4))
x

    
#more efficient version
loc.mix = function(n, p, mu1, mu2, Sigma) 
{
    #generate sample from BVN location mixture, version 2
    n1 = rbinom(1, size = n, prob = p)
    n2 = n - n1
    x1 = mvrnorm(n1, mu = mu1, Sigma)
    x2 = mvrnorm(n2, mu = mu2, Sigma)
    X = rbind(x1, x2)            #combine the samples
    return(X[sample(1:n), ])      #mix them
}

x = loc.mix(10000, 0.5, rep(0, 4), 2:5, Sigma = diag(4))
x
    
    
jpeg("fig7.jpeg", height=800, width=800, quality = 100)
r = range(x) * 1.2
par(mfrow = c(2, 2))
for (i in 1:4)
    hist(x[ , i], xlim = r, ylim = c(0, .3), freq = FALSE,
    main = "", breaks = seq(-5, 10, 0.5))
dev.off()

detach(package:MASS)



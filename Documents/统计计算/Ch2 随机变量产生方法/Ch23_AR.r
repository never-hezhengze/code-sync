### Example  (Acceptance-rejection method)
n = 1000
k = 0                 #counter for accepted
j = 0                 #iterations
y = numeric(n)

while (k < n) 
{
    u = runif(1)
    j = j + 1
    x = runif(1)  
    if (x * (1-x) > u) 
    {
        k = k + 1
        y[k] = x
    }
}

y
j

#compare empirical and theoretical percentiles
p = seq(.1, .9, .1)
Qhat = quantile(y, p)   #sample quantiles 
Q = qbeta(p, 2, 2)      #theoretical quantiles
se = sqrt(p * (1-p) / (n * dbeta(Q, 2, 2))) 
round(rbind(Qhat, Q, se), 3)


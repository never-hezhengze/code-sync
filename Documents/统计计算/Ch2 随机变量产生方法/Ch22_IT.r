### Example (Inverse transform method, continuous case)
n = 1000
u = runif(n)
x = u^(1/3)
x
    
jpeg("fig1.jpeg", height=800, width=800, quality = 100)
hist(x, prob = TRUE, main = expression(f(x)==3*x^2))
x = seq(0, 1, 0.01)
lines(x, 3*x^2)    
dev.off()

 
### Example (Inverse transform method, exponential)
myrexp = function(n, lambda)
{
    u = runif(n)
    x = -log(u)/lambda
}

x = myrexp(1000, lambda=1) 
x


### Example  (Inverse transform method, Binomial)
n = 1000
p = 0.4
u = runif(n)
x = as.integer(u > 1-p)   

mean(x)
var(x)
    

### Example  (Inverse transform method, Geometric)
n = 1000
p = 0.4
u = runif(n)
    
# Method 1
k = ceiling(log(1-u) / log(1-p))
k

# Method 2
k = floor(log(u) / log(1-p))+1
k


### Example  (Inverse transform method, Logarithmic)
#returns a random logarithmic(theta) sample size n
rlogarithmic = function(n, theta)  
{
    u = runif(n)
        
    N = ceiling(-16 / log10(theta))     #set the initial length of cdf vector
    k = 1:N
    a = -1/log(1-theta)
    fk = exp(log(a) + k * log(theta) - log(k))
    Fk = cumsum(fk)
        
    x = integer(n)
    for (i in 1:n) 
    {
        x[i] = as.integer(sum(u[i] > Fk))
            
        while (x[i] == N) #if x==N we need to extend the cdf
        {
            logf = log(a) + (N+1)*log(theta) - log(N+1)
            fk = c(fk, exp(logf))
            Fk = c(Fk, Fk[N] + fk[N+1])
            N = N + 1
            x[i] = as.integer(sum(u[i] > Fk))
        }#very unlikely because N is large
    }
    x + 1
}

n = 1000
theta = 0.5
x = rlogarithmic(n, theta)
x
    
#compute density of logarithmic(theta) for comparison
k = sort(unique(x))
p = -1 / log(1 - theta) * theta^k / k
se = sqrt(p*(1-p)/n)   

round(rbind(table(x)/n, p, se),3)
    
    
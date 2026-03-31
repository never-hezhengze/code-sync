## uniform RNG in R
runif(100)
runif(100, 2, 10)

set.seed(222)
runif(10)


## random generators of common probability distribution
rbinom(50, size=1, prob=0.5)
rexp(100, rate=0.2)
rnorm(100, mean=0, sd=0.5)

 
## sample 
sample(0:1, size=10, replace=TRUE)

x=sample(1:3, size=100, replace=TRUE, prob=c(0.2,0.3,0.5))
x
table(x)
prop.table(table(x))
   
sample(letters)
 
airquality
subset = sample(1:nrow(airquality), size=50)
mysample = airquality[subset, ]
print(mysample)


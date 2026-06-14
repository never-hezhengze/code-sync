## uniform RNG in R (random uniform)
runif(100)   ## 产⽣0到1上的⻓度为n的向量
runif(100, 2, 10)   ## 产生2到10上的长为100的向量

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
table(x)    ## 统计频数
prop.table(table(x))    ## 计算频率
   
sample(letters)    ## 表示将26个字母随机打乱顺序
 
airquality     ## R自带的数据集
subset = sample(1:nrow(airquality), size=50)
mysample = airquality[subset, ]
print(mysample)


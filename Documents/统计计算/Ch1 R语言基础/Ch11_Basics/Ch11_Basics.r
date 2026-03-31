## 显示 ##
n=10
n
print(n)

n=1:30
n
print(n)

## 帮助 ##
help(solve)

?solve

help("[[")       # 对有语法意义的，需要应用双引号或单引号

help("if")

help("bs")       # 默认在载入内存的包中搜索
help("bs", try.all.packages = TRUE) # 在所有包中搜索

library(splines)  # 加载包
help("bs")

help.start()      # 启动HTML格式帮助文档

help.search("tree") # 列出所有在帮助页码含有“tree”的函数
help.search("tree", rebuild = TRUE) # 刷新数据库

??tree

example(mean)


## source 运行 ##
## Ex_source

## sink 保存
## Ex_sink


## 命令行
name = "Carmen"; n1 = 10; n2 = 100; m = 0.5

name = "Carmen"
n1 = 10
n2 = 100
m = 0.5

a=5+6
  
## 列出对象 ##
name = "Carmen"; n1 = 10; n2 = 100; m = 0.5
ls()            # 列出当前进程中所有的对象
ls(pat = "m")   # 名称中包含m的对象
ls(pat = "^m")  # 名称中以m开头的对象

rm(name)        # 从内存中删除对象
print(name)


## 对象属性 ##
x = 1
mode(x)     # 查看对象的类型
length(x)   # 查看对象的长度

A = "Gomphotherium"; compar = TRUE; z = 1i
mode(A); mode(compar); mode(z)

## 缺失数据
NA           

## 大数
N = 2.1e23
N

x = 5/0
x

exp(x)
exp(-x)
x-x

## 转换类型
z=0:9
z
digits=as.character(z)
digits
as.numeric(digits)->x
x
mode(x)

## 获取和设定路径
getwd()
setwd("")

## 读取数据 ##
## Ex_read

## 存储数据 ##
## Ex_write


## 向量的生成 ##
x=c(1,2,3,4,5)
x

y=1:5
y

ch=c("sa","ba")
ch

## seq
z=seq(1,5)
z

1:5-1
1:(5-1)

w=seq(from=0, to= 10, by = 1)
w
z=seq(from=0, to= 10, length.out = 10)
z

## 画图
jpeg("fig1.jpeg")
x=seq(from=-10, to=10, by=0.02)
y=x^2
plot(x,y)
dev.off()

## scan
z = scan()

## rep
rep(1,3)
rep(c(1,2),2)
rep(1:3,1:3)
rep(1:2,each=2)

x=c(1,2,3)
x
u=rep(x, 10)
u

## gl
gl(2,3)
gl(2,3,length=4)
gl(2,2,label=c("F","M"))

## 随机生成特定分布
dnorm(4, 2, sqrt(4))    ## density
pnorm(4, 2, sqrt(4))    ## distribution

alpha=0.05
qnorm(1-alpha/2, 0, 1)  ## quantile

rnorm(1000, 0, 1)       ## random sampling


## 生成各种对象 ##
## vector
vector(mode = "logical", length = 0)

x=1:3
as.vector(x, mode = "any")
is.vector(x, mode = "any")
x[2]

## matrix
matrix(data=5, nr=2, nc=2)
matrix(1:6, 2, 3)
matrix(1:6, 2, 3, byrow=TRUE)

x = 1:6
dim(x) = c(2, 3)
x

A=matrix(1:100, nrow=10, ncol=10)
A

A[3, 4]
A[,1]
A[2,]

## data.frame
x = 1:2; n = 10; M = c(10, 35); y = 2:4
data.frame(x, n)

data.frame(A=x, B=M)

data.frame(x, y)

df=data.frame(
  Name=c("Alice", "Becka", "James", "Jeffrey", "John"), 
  Sex=c("F", "F", "M", "M", "M"), 
  Age=c(13, 13, 12, 13, 12),
  Height=c(56.5, 65.3, 57.3, 62.5, 59.0),
  Weight=c(84.0, 98.0, 83.0, 84.0, 99.5)
)
print(df)

df$Weight
df$Age

## array 
x=array(1:2,dim=c(2,2,2))
x
x[1, , ]
x[ , 2, ]

## list
x=1:2
y=2:4
L2=list(A=x,B=as.character(y))
L2
names(L2)
L2$A

## expression
exp1 = expression(x/(y+exp(z))) 
exp1

x = 3; y = 2.5; z = 1
x/(y+exp(z))

exp1 = expression(x/(y + exp(z)))    ## 构建表达式，不求值
exp1
eval(exp1)                           ## 对表达式求值


## 赋值运算 ##
value=1:10

x<-value
x

x<<-value
x

value->x
x

value->>x
x

x=value
x

## 常用运算 ##
x=c(-1, 0, 2)
y=c(3, 8, 2)

x+y
x-y
x*y
x/y
x^2
y^x

v=2*x+y+1
v

5%%3
5%/%3

1>2
3<=3
1==3
1!=3

T&F
T|F
!T

a=T
b=c(T, F)
a&b
a|b
xor(a, b)

all(1:7>3) 
any(1:7>3) 

2^2^3
1-1-1

## substr & paste ##
colors = c("red", "yellow", "blue")
colors
more.colors = c(colors, "green", "magenta", "cyan")
more.colors

substr(colors, 1, 2)

paste(colors, "flowers")
paste("several ", colors, "s", sep="")
paste("I like", colors, collapse = ", ")


## 对象的提取 ##
x = 1:5
x

x[3]
x[c(1,3)]
x[3:5]
x[x>2]
x[-2]
x[-c(1,3)]

x[c(F,T)]

x[0.5]
x[1.5]

x = matrix(1:6, 2, 3)
x

x[1, 2]
x[2, ]
x[, 3]
x[, 2:3]
x[-1,]


x=1:3 
names(x) 

names(x)=c("a","b","c") 
x
x["b"]


x=matrix(1:4,2)
x

rownames(x)=c("r1","r2")
colnames(x)=c("c1","c2")
x
x["r2",]

dimnames(x)=list(c("R1","R2"),c("C1","C2"))
x
x["R2",]


x=matrix(1:4,2); y=1:3
z=list(A=x, B=y)
z
z$A
z$B


## 向量运算 ##
x = 1:4 
y = rep(1, 4)
z = x + y
z

x = 1:2 
y = rep(1, 4)
z = x + y
z

x = 1:3
y = rep(1, 4)
z = x + y
z

a = 10
z = a * x
z

x=c(1,2,3)
y=c(2,4,6,8,10)

exp(x)
sqrt(y)
log(y)

z=c(-1,2,4)
b=exp(z)
b
a=sqrt(z)
a

x=c(10, 6, 4, 7, 8)
min(x)
max(x)
range(x)

which.max(x)
which.min(x)

sum(x)
prod(x)
length(x)

x=3.789
ceiling(x)
floor(x)
trunc(x)
round(x, 2)

x=rnorm(100, 0, sqrt(2))
print(x)

median(x)
mean(x) 
var(x)
sd(x)
cv=sd(x)/mean(x)

## 矩阵运算 ##
A=matrix(1:4,2,2)
A

B=diag(2)
B

v=rep(1, 5)
v
I5=diag(v)
I5 

p=10
I=diag(rep(1, p))
I 

A=matrix(1:9, nrow=3)
A
a=diag(A)
a 

A=matrix(1:9, nrow=3)
A
B=diag(diag(A))
B

A=matrix(1:4,2,2)
A

B=diag(2)
B

A+B
A-B
A*B
B/A

A%*%B

A=matrix(1:4,2,2)
B=matrix(rep(1,4),2,2)
kronecker(A,B)

dim(A)
nrow(A)
ncol(A) 
t(A)
det(A)

eigen(A)

solve(A)

A=matrix(1:9, nrow=3, byrow=T)
A[3,3]=10
A
b=rep(1,3)
b
x=solve(A,b)
x
D=solve(A)
D

B=diag(c(100000000000, 0.00001))
B
det(B)
solve(B)
rcond(B)>.Machine$double.eps

if(rcond(B)>.Machine$double.eps)
{B.inv=solve(B)}
if(rcond(B)<=.Machine$double.eps)
{cat("the matrix is computationally sigular!")}

A=matrix(1:9, 3, 3)
A
B=matrix(rep(1,9), 3, 3)
B
cbind(A, B)
rbind(A, B) 

lower.tri(A,diag=T)

B[lower.tri(A,diag=T)]=0


## 奇异值分解
A
A.svd=svd(A)
A.svd

A.svd$u%*%diag(A.svd$d)%*%t(A.svd$v)


## Choleski分解
B=matrix(c(1,2,3,2,5,6,3,6,10), nrow=3, ncol=3)
B
chol(B)

## QR分解
B
qr.B=qr(B)
qr.B

Q=qr.Q(qr.B)
R=qr.R(qr.B)
Q%*%R

## 条件数
kappa(B)


## apply
A=matrix(1:12, nrow=3, ncol=4)
A
rowSums(A)
rowMeans(A)
colSums(A)
colMeans(A) 

apply(A, 1, sum)
apply(A, 2, mean)
apply(A, 1, var)
apply(A, 2, sd)
apply(A, 1, prod)


## 绘图设备
## 多图显示
## Ex_plot


## 高级绘图
## 低级绘图
## 绘图参数

## 几种绘图举例

## 查看点pch的各个形状
plot(rep(1,10),ylim=c(-2,1.2),pch=1:10,cex=3,axes=F,xlab="",ylab="")
text(rep(0.6,10),as.character(1:10))
points(rep(0,10),pch=11:20,cex=3)
text(rep(-0.4,10),as.character(11:20))
points(rep(-0.8,5),pch=21:25,cex=3)
text(rep(-1.2,5),as.character(21:25))
points(6:10, rep(-0.8,5),pch=c("*","?","X","x","&"),cex=3)
text(6:10,rep(-1.2,5),c("*","?","X","x","&"))


## 统计分析
## 线性回归
## Ex_lm

## 聚类分析
## Ex_cluster


## package
search()

library(survival)

data()


## 控制流
# for
Fib=rep(0,20)
Fib[2]=1
for(i in 3:20) Fib[i]=Fib[i-1]+Fib[i-2]
Fib

#while
Fib=rep(0,20)
Fib[2]=1
i=3
while(i<=20){Fib[i]=Fib[i-1]+Fib[i-2];i=i+1}
Fib

# if else
x=3
if(x>2)y=2*x else y=3*x
y

# repeat
Fib=rep(0,20)
Fib[2]=1
i=3
repeat { Fib[i]=Fib[i-1]+Fib[i-2]; i=i+1; if(i>20) break}
Fib


# function
ft=function(m) ## 自然数阶乘
{
  if(m==1) 
    {rlt=1}
  else
    {rlt=m*ft(m-1)}
  return(rlt)
}

ft(1)
ft(3)


## Ex_tailsum


## 程序优化
X=rnorm(100000)
Y=rnorm(100000)

Z=c()
system.time({
for(i in 1:100000)
  {
  Z=c(Z, X[i]+Y[i]) 
}
})


Z=rep(0, 100000)
system.time({
for(i in 1:100000)
  {
  Z[i]=X[i]+Y[i]
}
})


system.time({
Z=X+Y
})



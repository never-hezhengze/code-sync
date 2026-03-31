######  hist   density   ################################################################################
mtcars
mpg=mtcars$mpg

jpeg("hist.jpeg", height=800, width=960, quality = 100)
opar=par(mfrow=c(2,2))

hist(mpg)

hist(mpg, breaks=12, col="grey", 
     xlab="Miles Per Gallon", main="histogram of mtcars")

hist(mpg, breaks=12, freq=F, col="darkseagreen", 
     xlab="Miles Per Gallon", main="histogram of mtcars")
lines(density(mpg), col="darkgreen", lwd=2)

hist(mpg, breaks=12, freq=F, col="darkseagreen", 
     xlab="Miles Per Gallon", main="histogram of mtcars")
lines(density(mpg), col="darkgreen", lwd=2)
xfit=seq(min(mpg), max(mpg), length=40)
yfit=dnorm(xfit, mean(xfit), sd(xfit))
lines(xfit, yfit, col="tomato4", lwd=2)

par(opar)
dev.off()


######  boxplot  ###############################################################################
mtcars
mpg=mtcars$mpg
mpg

jpeg("mbox1.jpeg", height=800, width=800, quality = 100)
boxplot(mpg)
dev.off()

jpeg("mbox2.jpeg", height=800, width=800, quality = 100)
opar=par(mfrow=c(2,2))
boxplot(mpg~cyl, data=mtcars, 
        main="mtcars data", xlab= "cylinders", ylab="miles per gallon")

boxplot(mpg~cyl, data=mtcars, col=4,
        main="mtcars data", xlab= "cylinders", ylab="miles per gallon")

boxplot(mpg~cyl, data=mtcars, col=rainbow(3),
        main="mtcars data", xlab= "cylinders", ylab="miles per gallon")

boxplot(mpg~cyl, data=mtcars, col=heat.colors(3, alpha = 0.4),
        main="mtcars data", xlab= "cylinders", ylab="miles per gallon")
par(opar)
dev.off()



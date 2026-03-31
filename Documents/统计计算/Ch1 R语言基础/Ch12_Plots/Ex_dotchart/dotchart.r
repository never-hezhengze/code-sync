######  dotchart  ###############################################################################
mtcars

jpeg("mdot1.jpeg", height=800, width=800, quality = 100)
dotchart(mtcars$mpg, labels=row.names(mtcars), 
        main="dotchart of mtcars data")
dev.off()

mtcars2=mtcars[order(mtcars$mpg),]
mtcars2$cyl=factor(mtcars2$cyl)
mtcars2$color[mtcars2$cyl==4]="red"
mtcars2$color[mtcars2$cyl==6]="blue"
mtcars2$color[mtcars2$cyl==8]="darkgreen"

jpeg("mdot2.jpeg", height=800, width=800, quality = 100)
dotchart(mtcars2$mpg, labels=row.names(mtcars2), 
         groups = mtcars2$cyl, gcolor = "black",
         color=mtcars2$color, pch=19, 
         main="dotchart of mtcars data")
dev.off()


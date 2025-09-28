/*用while循环计算自然指数e，直到最后一项小于10的-6次方*/ 
#include <stdio.h> 

int main()
{
	double e = 1;
	int n = 1,i;
	double factor = 1;				//factor用来储存最后一项的值 
	
	while(factor >= 0.000001)
	{	
		factor = 1;
		for(i = 1;i <= n;i++)
			{
			factor *= i;			//先计算n的阶乘 
			}
		factor = 1.0 / factor;		//再取倒数储存在factor中
		e += factor;				//e累加 
		n++;
	}					
	
	printf("e=%lf",e);
		
	return 0 ;
}

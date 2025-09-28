//求Fibonacci数列的前12项 
#include <stdio.h> 

int main()
{
	int i, m = 0, n = 1;
	for(i = 1; i <= 12; i++)
	{
		m = m + n;				//m取前两项之和 
		n = m - n;				//n保留计算出m后m的前一项的值，用于下一次求和 
		printf("%d ", m);
	}
	return 0 ;
} 

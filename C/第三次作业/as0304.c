//输出2~1000之间的所有完数 
#include <stdio.h> 

int main()
{
	int i, j;
	printf("2~1000的所有完数有：\n");
	
	for(i = 3;i <= 1000;i++)
	{
		int sum = 0;
		for(j = 1; j <= i / 2; j++)
		{
			if(i % j == 0)				//i可以整除j时 执行 
				sum += j;			//累计求i的因子之和 
		}
		if(i == sum)
			printf("%d ", i);		//输出完数 
	}
	
	return 0 ; 
} 

//随机生成十道小学生除法题 ，并判卷，每题十分 
#include <stdio.h> 
#include <time.h>
#include <stdlib.h>

int main()
{
	int x, y, s, t = 0, i;
	srand((int)(time(0)));
	for(i = 1; i <= 10; i++)
	{
		do
		{
			x = rand() % 181 + 20;
			y = rand() % 8 + 2;
		}while(x % y);
		
		printf("%d/%d=\n", x, y);
		printf("Please input the answer:\n");
		scanf("%d", &s);
		
		if (s == x / y)
		{
			t += 10;
			printf("OK!\n\n");
		}
		else
			printf("Error!\n");
	}
	
	printf("score = %d\n", t);
	
	return 0 ;
}

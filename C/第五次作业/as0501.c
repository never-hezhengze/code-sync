#include <stdio.h>

/*找到30000以内的所有完备数*/
int is_complete(int num);

int main()
{
	int i;
	printf("30000以内的所有完备数有：\n");
	for (i = 1;i < 30000;i++)
	{
		if (is_complete(i))
			printf("%d ",i);
	}
	return 0 ;
} 

//定义is_complete 
int is_complete(int num)
{
	int i,sum = 0;
	for(i = 1;i < num;i++)
	{
		if (num % i == 0)
			sum += i;
	}
	if(sum == num)
		return 1;
	else
		return 0;
}
 

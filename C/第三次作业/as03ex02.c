#include <stdio.h>
#include <math.h>

int main()
{
	float rate;
	int year = 0;
	
	printf("请输入年利率：\n");
	scanf("%f",&rate);
	
	while (1)
	{
		if (1 * pow((1 + rate),year) >= 2)
			break;
		year += 1;
	}
	printf("翻倍需要%d年",year);
	
	return 0 ;
} 

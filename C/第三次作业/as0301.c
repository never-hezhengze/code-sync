#include <stdio.h>     //输出整数的位数 

int main()
{
	int num, size = 1;
	
	printf("请输入一个正整数：");
	scanf("%d", &num);
	
	while(num / 10 != 0)
		{
		size += 1;
		num /= 10;				//位数+1的同时，num通过整除10减少一位 
		}
	
	printf("这个正整数的位数为：%d", size);
	
	return 0;
}

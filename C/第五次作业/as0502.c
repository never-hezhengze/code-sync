#include <stdio.h>
#include <math.h>

/*
改写哥德巴赫猜想验证程序 
*/

//提示用户输入符合要求的整数 
int GetData();

//判断一个整数是否是素数
int IsPrime(int num); 

//验证单个偶数是否符合猜想 
int Goldbach(int num);



int main()
{
	int n,m;
	do
	{
		n = GetData();
		if(Goldbach(n))
		{
			printf("该数符合哥德巴赫猜想\n"); 
		}
		else
		{
			printf("不符合哥德巴赫猜想\n");
		}
		printf("要继续程序吗？(输入1继续，输入0退出)");
		scanf("%d",&m);
	}while(m);
	
	return 0 ;
}

//定义GetData提示用户输入 
int GetData()
{
	int num;
	printf("输入一个不小于6的偶数：");
	scanf("%d",&num);
	while (num <= 6 || num % 2)
	{
		printf("输入的数不符合要求！请重新输入：");
		scanf("%d",&num); 
	}
	return num ;
}

//定义IsPrime判断是否是素数 
int IsPrime(int num)
{
	int i, isprime = 1;
	for(i = 2;i <= pow(num,0.5);i++)
	{
		if (num % i == 0)
			isprime = 0;
	}
	return isprime ;
}

//定义Goldbach验证哥德巴赫猜想
int Goldbach(int num)
{
	int i,is_goldbach = 0;
	for(i = 3; i < num / 2; i++)
	{
		if(IsPrime(i) && IsPrime(num - i))
			{
				is_goldbach = 1;
				break;
			}
			
	}
	return is_goldbach ;
}


#include <stdio.h>
#define N 4 

int main()
{
	float a[N],temp,ave,sum = 0;
	int i,j,flag = 0;
	printf("请输入%d个数:\n", N);
	for(i = 0;i < N;i++)
		scanf("%f",&a[i]);
	//冒泡排序法将成绩排序并打印 
	for(i = 0;i < N-1;i++)
	{
		for(j = i+1;j < N;j++)
		{
			if(a[j] > a[i])
			{
				temp = a[j];
				a[j] = a[i];
				a[i] = temp;
			}
		} 
	}
	printf("排序后的%d个数:\n",N);
	for(i = 0;i < N;i++)
	{
		printf("%.1f  ",a[i]);
	}
	printf("\n");
	//计算平均成绩 
	for(i = 0;i < N;i++)
	{
		sum += a[i];
	}
	ave = sum / N;
	printf("平均成绩为:%.2f",ave);
	//统计高于平均分的人数
	for(i = 0;i < N;i++)
	{
		if(a[i] > ave)
			flag += 1;
	}
	printf("高于平均分的有%d人",flag);
	return 0 ;
} 

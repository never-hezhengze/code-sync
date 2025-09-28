#include <stdio.h>
#define N 8

int main()
{
	int score[N],i;
	int max_score = 0,min_score = 0;
	int sum = 0;
	float average;
	printf("请输入评委的打分：（）");
	
	for(i = 0;i <= N - 1;i++)
	{
		scanf("%d",&score[i]);
	}
	
	for(i = 0;i <= N - 1;i++)
	{
		if(score[max_score] < score[i])
			max_score = i;
	}
	for(i = 0;i <= N - 1;i++)
	{
		if(score[min_score] > score[i])
			min_score = i;
	}
	
	for(i = 0;i <= N - 1;i++)
	{
		sum += score[i];
	}
	
	sum = sum - (score[max_score] + score[min_score]);
	average = (float)sum / (float)(N - 2);
	printf("最高分为%d\n",score[max_score]);
	printf("最低分为%d\n",score[min_score]);
	printf("选手的最后得分是%.1f",average);
	
	return 0 ;
} 

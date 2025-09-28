/*输入N个学生的三门课成绩，输出三门课各自的平均分及最高分*/
#include <stdio.h>
#define N 5
int main()
{
	float a[N][3], score[3], max;
	float(*p)[3];
	int i;
	printf("请输入%d个学生的三门课成绩：\n",N);
	for(p = a;p < a + N;p++)
	{
		for(i = 0;i < 3;i++)
		{
			scanf("%f",(*p)+i);
		}
	}
	printf("三门课平均成绩及最高分：\n");
	for(i = 0;i < 3;i++)
	{
		score[i] = 0;
		max = 0;
		for(p = a;p < a + N;p++)
		{
			score[i] += (*p)[i];
			if ((*p)[i]> max)
			{
				max = (*p)[i];
			}
		}
		printf("第%d门课\t平均分:%f\t最高分:%f\n",i + 1, score[i]/5, max);
	}
	return 0 ;
} 

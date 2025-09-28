#include <stdio.h>
#define M 6
#define N 5

int main()
{
	int a[M][N],i,j,k,t;
	int* *p,*pa[M];
	printf("请输入%d行数据，每行%d个整数：\n",M,N);
	for(i = 0;i < M;i++)
	{
		for(j = 0;j < N;j++)
		{
			scanf("%d",&a[i][j]);
		}
	}
	for(i = 0;i < M;i++)
		pa[i] = a[i];
		
	//冒泡排序 
	for (i = 0; i < M; i++) // 遍历每一行
    {
        for (j = 0; j < N - 1; j++) // 冒泡排序的外层循环
        {
            for (k = 0; k < N - j - 1; k++) // 冒泡排序的内层循环
            {
                if (pa[i][k] < pa[i][k + 1])
                {
                    t = pa[i][k];
                    pa[i][k] = pa[i][k + 1];
                    pa[i][k + 1] = t;
                }
            }
        }
    }
	
	printf("排序结果：\n");
	for(i = 0;i < M;i++)
	{
		for(j = 0;j < N;j++)
			printf("%d ",a[i][j]);
		printf("\n");
	}
	return 0 ;
} 

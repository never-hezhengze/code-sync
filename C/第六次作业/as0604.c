#include <stdio.h>
#define N 10

int  *findMax(int  *a,int n,int  *p)
{
	int i;
    int *max = a; // 假设第一个元素是最大值
    *p = 0;       

    for (i = 1; i < n; i++) // 从第二个元素开始遍历
    {
        if (*(a + i) > *max) // 如果当前元素大于最大值
        {
            max = a + i;
            *p = i;     
        }
    }
    return max; // 返回最大值的指针
}

int main()
{
	int a[N],*p,pos;
	printf("请输入%d个整数：",N);
	for(p = a;p < a+N;p++)
	{
		scanf("%d",p);
	}
	p = findMax(a,N,&pos);
	printf("数组中第%d个元素最大，元素值为%d\n",pos+1,*p);
	return 0 ;
}

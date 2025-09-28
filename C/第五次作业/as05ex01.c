/*
用递归函数找到列表中的最大数 
*/
#include <stdio.h>

float mymax(float list[],int len);

int main()
{
	int len;
	int i;
	printf("请输入数字个数：");
	scanf("%d",&len);
	
	float arr[len],arr_max;
	printf("请输入%d个数：");
	for (i = 0;i < len;i++)
	{
		scanf("%f",&arr[i]);
	}
	arr_max = mymax(arr,len);
	printf("列表中的最大数是%f",arr_max);
	
	return 0 ;
}

float mymax(float list[],int len)
{
	float result,rest_max;
	result = list[0];
	if (len == 1)
	{
		return result;
	}
	else
	{
		rest_max = mymax(&list[1],len-1);
		return (result>rest_max)? result:rest_max;
	}
}


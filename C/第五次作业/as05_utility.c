#include <stdio.h>
//计算一个数组内元素的平均值 
float AverageTemp(float arr[],int len)
{
	float sum = 0,ave;
	int i;
	for (i = 0;i < len;i++)
	{
		sum += arr[i];
	}
	ave = sum / len;
	return ave;
}

//得到数组内最大元素的序号 
int MaxTemp(float arr[],int len)
{
	int i,key = 0;
	float max_arr = arr[0];
	for (i = 0;i < len;i++)
	{
		if (arr[i] > max_arr)
		{
			max_arr = arr[i];
			key = i;
		}
	}
	return key ;
}

//得到数组内最小元素的序号
int MinTemp(float arr[],int len)
{
	int i,key = 0;
	float min_arr = arr[0];
	for (i = 0;i < len;i++)
	{
		if (arr[i] < min_arr)
		{
			min_arr = arr[i];
			key = i;
		}
	}
	return key ;
} 

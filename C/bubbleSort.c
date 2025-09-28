#include <stdio.h>

int main()
{
	int arr[] = {24,11,25,37,57,93,47,59,26};
	int length,i,j,temp;
	length = sizeof(arr) / sizeof(arr[0]);
	for(i = 0;i < length - 1;i++)
	{
		for(j = 0;j < length - 1 - i;j++)
		{
			if(arr[j] > arr[j+1])
			{
				temp = arr[j];
				arr[j] = arr[j+1];
				arr[j+1] = temp;
			}
		}
	}
	for(i = 0;i < length;i++)
	{
		printf("%d ",arr[i]);
	}
	return 0;
}










/*
编写程序，从用户输入的一组整数中找到全部偶数。
要求定义一个函数FindEvenNumbers通过接受一组整数
把找到的偶数和它们的个数通过参数或返回值传递给主函数
*/
#include <stdio.h>
#include <conio.h>
#define SIZE 10
//声明函数FindEvenNumbers 
void FindEvenNumbers(int arr[],int size,int even[],int* count);

int main()
{
	int list[SIZE];
	int even[SIZE] = {0};
	int count;
	int i;
	printf("输入%d个整数：\n",SIZE);
	for (i = 0;i < SIZE;i++)
		scanf("%d",&list[i]);
	FindEvenNumbers(list,SIZE,even,&count);
	printf("有%d个偶数：\n",count);
	for(i = 0;i < count;i++)
		printf("%d ",even[i]);
	printf("\n");
	printf("请按任意键继续...");
	getch();
	return 0 ;
} 



//定义函数 FindEvenNumbers
void FindEvenNumbers(int arr[], int size,int even[],int* count)
{
	int j;
	*count = 0;
	for(j = 0;j < size;j++)
	{
		if(arr[j] % 2 == 0)
			{
				even[*count] = arr[j];
				(*count)++;
			}
	} 
}

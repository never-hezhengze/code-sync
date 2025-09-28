//计算两个矩阵的乘积 
#include <stdio.h>

int main()
{
	int rows_1,cols_1,rows_2,cols_2,i,j,k;
	printf("请输入第一个矩阵的行数和列数(用空格隔开)\n");
	scanf("%d %d",&rows_1,&cols_1);
	printf("请输入第二个矩阵的行数和列数(用空格隔开)\n");
	scanf("%d %d",&rows_2,&cols_2);
	float matrix1[rows_1][cols_1], matrix2[rows_2][cols_2],goal_matrix[rows_1][cols_2];
	//判断是否合法并读取用户输入的矩阵 
	if(cols_1 != rows_2)   //判断是否可以相乘 
		printf("这两个矩阵无法相乘！");
	else 
	{
		printf("请输入第一个矩阵：\n"); 
		for(i = 0;i < rows_1;i++)
		{
			for(j = 0;j < cols_1;j++)
			{
				scanf("%f", &matrix1[i][j]);
			}
		}
		printf("请输入第二个矩阵：\n"); 
		for(i = 0;i < rows_2;i++)
		{
			for(j = 0;j < cols_2;j++)
			{
				scanf("%f", &matrix2[i][j]);
			}
		}
		//计算矩阵的乘积 
		for(i = 0;i < rows_1;i++)
		{
			for(j = 0;j < cols_2;j++)
			{
				goal_matrix[i][j] = 0;
				for(k = 0;k < cols_1;k++)
					goal_matrix[i][j] += matrix1[i][k] * matrix2[k][j];
			}
		}
	}
	//输出他们的乘积
	printf("这两个矩阵的乘积是：\n"); 
	for(i = 0;i < rows_1;i++)
	{
		for(j = 0;j < cols_2;j++)
		{
			printf("%.2f ",goal_matrix[i][j]);
		}
		printf("\n");
	}
	 
	return 0 ; 
} 


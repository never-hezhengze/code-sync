#include <stdio.h>
#define N 20
#define M 3 
/*
约瑟夫游戏 
轮流报数1、2、、、M，报号为M的人退出 
*/

// 定义结构体类型
typedef struct player
{
	int num;   //编号 
	int status;  //1：出圈；0：在圈内 
} Player; 

//主函数 
int main()
{
	Player players[N];
	int i,j; 
	int count; 
	//给所有人编号
	for(i = 0;i < N;i++)
	{
		players[i].num = i + 1;
		players[i].status = 0;
	}
	
	//游戏循环
	i = 0;
	j = 1;
	while(count < N)
	{
		if(players[i].status == 0)
		{
			if(j % M == 0)
			{
				players[i].status = 1;
				count ++;
				printf("编号%d出圈\n",players[i].num); 
			}
			j++;
		}
		i++;
		if(i == N)
			i = 0;
	} 
	
	 
	return 0 ;
} 

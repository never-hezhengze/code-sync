/*
五子棋游戏胜负判定 
在用户每次下一颗棋子之后，对该棋子的四个方向进行遍历，寻找是否有五颗棋子连成一线 

*/
#include <stdio.h>
#include "judgement.h"
/*
Judgement函数判断游戏胜负

输入参数说明： 
checkboard是一个15 ×15的二维数组，记录棋盘状态
	数组元素说明：0代表此处没有任何棋子，1代表此处放有一颗黑子，2代表此处放有一个白子 
	 
new_chessman_x是最新落子在二维数组中的第一个坐标  
new_chessman_y是最新落子在二维数组中的第二个坐标
从0取到14 

输出参数说明：
result是一个全局变量，用于记录比赛结果，值为0代表比赛还未分出胜负，值为1代表黑子获胜，值为2代表白子获胜(和checkerboard元素对应)
当判断出五子连线时，将key赋值给result，否则return0，不对result做任何更改 
*/

//int result = 0; 
int Judgement(int checkerboard[][15],int len,int new_chessman_x,int new_chessman_y)
{
	//将棋盘中间的落子和棋盘边缘的落子分开判断
	int key = checkerboard[new_chessman_x][new_chessman_y];     //key储存本次判断中最新落子的属性 
	int count_i = 0,count_j = 0,count_k = 0,count_v = 0;        //分别对四个方向上的key属性棋子计数  i--竖向  j--横向  k--左斜向  v--右斜向 
	int i;
	int count1 = 0,count2 = 0;                                  //辅助每个方向上的计数 
	int result = 0;
	
	//竖向判断，以 [new_chessman_x][new_chessman_y]为中心向上、向下进行搜索 
	//count1记录向上搜索得到的连子数，count2记录向下搜索得到的连子数 
	i = 1;
	while((new_chessman_y + i) < 15 && i <= 4)   //最多向上搜索四个，一旦发现到达棋盘上边缘退出循环 
	{
		if(checkerboard[new_chessman_x][new_chessman_y+i] == key)
			count1 ++;
		else           //一旦发现非key子，直接退出while循环，此时的count1就是向上的连子数 
			break;
		i++;
	}
	i = 1;
	while((new_chessman_y - i) >= 0 && i <= 4)   //向下搜索同理 
	{
		if(checkerboard[new_chessman_x][new_chessman_y-i] == key)
			count2 ++;
		else
			break;
		i++;
	}
	count_i = 1 + count1 + count2;
	if (count_i >= 5)
	{
		result = key;
		return result; 
	}
		
	
	 
	//横向判断，以 [new_chessman_x][new_chessman_y]为中心向左、向右进行搜索 
	//count1记录向右搜索得到的连子数，count2记录向左搜索得到的连子数 
	i = 1,count1 = 0,count2 = 0;     //每次计数前初始化 
	while((new_chessman_x + i) < 15 && i <= 4)   //最多向右搜索四个，一旦发现到达棋盘右边缘退出循环 
	{
		if(checkerboard[new_chessman_x+i][new_chessman_y] == key)
			count1 ++;
		else           //一旦发现非key子，直接退出while循环，此时的count1就是向右的连子数 
			break;
		i++;
	}
	i = 1; 
	while((new_chessman_x - i) >= 0 && i <= 4)   //向左搜索同理 
	{
		if(checkerboard[new_chessman_x-i][new_chessman_y] == key)
			count2 ++;
		else
			break;
		i++;
	}
	count_j = 1 + count1 + count2;
	if (count_j >= 5)
	{
		result = key;
		return result; 
	} 
	
	
	//左斜向判断，以 [new_chessman_x][new_chessman_y]为中心向左斜向上、向右斜向下进行搜索 
	//count1记录向左斜向上搜索得到的连子数，count2记录向右斜向下搜索得到的连子数 
	i = 1,count1 = 0,count2 = 0;     //每次计数前初始化   
	while((new_chessman_x - i) >= 0 && (new_chessman_y + i) < 15 && i <= 4) 
	{
		if(checkerboard[new_chessman_x-i][new_chessman_y+i] == key)
			count1 ++;
		else           //一旦发现非key子，直接退出while循环，此时的count1就是向左斜向上的连子数 
			break;
		i++; 
	}
	i = 1;
	while((new_chessman_y - i) >= 0 && (new_chessman_x + i) < 15 && i <= 4) 
	{
		if(checkerboard[new_chessman_x+i][new_chessman_y-i] == key)
			count2 ++;
		else           //一旦发现非key子，直接退出while循环，此时的count2就是向右斜向下的连子数 
			break;
		i++; 
	}
	count_k = 1 + count1 + count2;
	if (count_k >= 5)
	{
		result = key;
		return result;
	} 
	
	
	//右斜向判断，以 [new_chessman_x][new_chessman_y]为中心向右斜向上、向左斜向下进行搜索 
	//count1记录向右斜向上搜索得到的连子数，count2记录向左斜向下搜索得到的连子数 
	i = 1,count1 = 0,count2 = 0;     //每次计数前初始化
	while((new_chessman_x + i) < 15 && (new_chessman_y + i) < 15 && i <= 4) 
	{
		if(checkerboard[new_chessman_x+i][new_chessman_y+i] == key)
			count1 ++;
		else           //一旦发现非key子，直接退出while循环，此时的count1就是向右斜向上的连子数 
			break;
		i++; 
	}
	i = 1;
	while((new_chessman_y - i) < 15 && (new_chessman_x - i) < 15 && i <= 4) 
	{
		if(checkerboard[new_chessman_x-i][new_chessman_y-i] == key)
			count2 ++;
		else           //一旦发现非key子，直接退出while循环，此时的count2就是向左斜向下的连子数 
			break;
		i++; 
	}
	count_v = 1 + count1 + count2;
	if (count_v >= 5)
	{
		result = key;
		return result; 
	}
	
	return 0;
} 




#include <stdio.h>
#include <string.h>
#include <windows.h>

int main()
{
	int a[20] = {0},j = 0,k = 0;
	int sum = 0;
	//创建20行的二维数组储存每个座位的状态，每一行对应一个座位 
	char isseat[20][10]; 
	
	while(sum <= 20)     //大循环退出的条件不应该是“循环20次后结束”，因为在头等舱售罄用户仍然选择头等舱时，程序指引用户重新选择 
	{					 //此时会消耗一次循环然而并未售出票，最后可能出现程序结束但是票未售完的情况 
		for(j = 0;j < 20;j++)
		{
			//未售出的座位用【】储存在isseat的一行中
			//已售出的座位用[]储存在isseat的一行中 
			char temp[10];
			if(a[j] == 0)
				sprintf(temp, "【%d】", j + 1);
			else
				sprintf(temp, " [%d] ", j + 1);
			strcpy(isseat[j], temp);
		}
		
		int choice;       //储存用户选择头等舱还是经济舱
		//打印菜单 
		printf("***********************************\n");
		printf("*         WHU航空订票程序         *\n");
		printf("*              菜单               *\n");
		printf("*    【1】按1选择头等舱           *\n");
		printf("*    【2】按2选择经济舱           *\n");
		printf("***********************************\n");
		scanf("%d",&choice);
		system("cls");
		
		int chose_seat = 0;    //储存用户选择的座位号 
		if(choice == 1)
		{
			//判断头等舱是否还有余位 
			if((a[0] + a[1] + a[2] + a[3] + a[4]) == 5)
			{
				printf("该趟次的头等舱已售罄，下一趟航班将在在三小时后起飞");
			}
			else
			{	//把isseat的第i行以字符串打印出来 
				printf("头等舱的座位分布如下：\n");
				printf("【】代表空座位，[]代表已售座位\n");
				printf("***********************************\n");
				printf("*   |                         |   *\n");
				printf("*   |    %s       %s    |   *\n",isseat[0],isseat[1]);
				printf("*   |    %s       %s    |   *\n",isseat[2],isseat[3]);
				printf("*   |    %s                |   *\n",isseat[4]);
				printf("*   |                         |   *\n");
				printf("***********************************\n");
				printf("输入对应的座位号来选择座位\n");
				scanf("%d", &chose_seat);
			}
		}
		else
		{
			printf("经济舱的座位分布如下：\n");
			printf("【】代表空座位，[]代表已售座位\n");
			printf("***********************************\n");
			printf("*   |                         |   *\n");
			printf("*   |    %s       %s    |   *\n",isseat[5],isseat[6]);
			printf("*   |    %s       %s    |   *\n",isseat[7],isseat[8]);
			printf("*   |    %s      %s   |   *\n",isseat[9],isseat[10]);
			printf("*   |    %s      %s   |   *\n",isseat[11],isseat[12]);
			printf("*   |    %s      %s   |   *\n",isseat[13],isseat[14]);
			printf("*   |    %s      %s   |   *\n",isseat[15],isseat[16]);
			printf("*   |    %s      %s   |   *\n",isseat[17],isseat[18]);
			printf("*   |    %s               |   *\n",isseat[19]);
			printf("输入对应的座位号来选择座位\n");
			scanf("%d", &chose_seat);
		}
		if (chose_seat != 0)                  //若头等舱已满，则chose_seat仍为初始值0，程序跳过该部分之间询问用户是否还要继续购票 
			if(a[chose_seat - 1] == 1)        //座位号与数组索引之间差1 
				printf("该座位已售!\n"); 
			else
			{
				printf("购票成功!\n");
				printf("您的登机牌如下：\n");
				printf("————————————————————————————————————————————————————\n");
				printf("|  姓名：XXX      证件号：XXXXXXXXXXXXX            |\n");
				printf("|  航班信息：WHU航空公司 HB-527次航班              |\n");
				printf("|  座位信息：%d 号座位                              |\n", chose_seat);
				printf("|              祝您旅途愉快！:)                    |\n");
				printf("————————————————————————————————————————————————————\n");
				a[chose_seat - 1] = 1;
			}
		Sleep(2000);
		system("cls");
	 	
		int iscontinue;
		printf("您还要继续购票吗？(输入1代表继续，0代表退出)\n");
		scanf("%d", &iscontinue);
		if (iscontinue == 0)
			break;
		else
		{
			Sleep(1000);
			system("cls");
		}
		//sum记录已售出座位数量 
		for(k = 0;k < 20;k++)
		{
			sum += a[k];
		}
	}
	return 0 ;
}

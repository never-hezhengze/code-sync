/*
	记忆测试游戏：
	计算机在屏幕上将一串数字显示很短的时间。
	玩家必须在数字消失之前记住它们，然后输入这串数字，每次过关后，计算机会显示更长的一串数字，让玩家继续玩下去。
	玩家应尽可能使这个过程重复更多的次数。

	ZhangHua @ 2018-10-19
*/

#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <ctype.h>
#include <windows.h>

int main()
{
	char play_again = 'y';

	printf("\n\n");
	printf("====================\n");
	printf("\n");
	printf("    记忆测试游戏\n");
	printf("\n");
	printf("          (C)2018 ZH\n");
	printf("--------------------\n");
	printf("计算机在屏幕上将一串\n"
		   "数字显示很短的时间。\n"
		   "玩家必须在数字消失之\n"
		   "前记住它们，然后输入\n"
		   "这串数字，每次过关后，\n"
		   "计算机会显示更长的一\n"
		   "串数字，让玩家继续玩\n"
		   "下去。玩家应尽可能使\n"
		   "这个过程重复更多的次\n"
		   "数。\n");
	printf("====================\n\n");
	system("pause");

	do
	{
		int sequence_length = 2; // 随机数串的长度
		int correct = 1; // 用户输入正确
		time_t seed; // 保存一次出题产生随机数序列的种子
		int correct_count = 0; // 一次游戏记忆正确的次数
		int time_taken = 0; // 一次游戏花费的时间

		system("cls");
		printf("\n开始游戏...\n");
		time_taken = clock();
		do
		{
			int i;
			int now; // 出题时间
			int try_count = 0; // 尝试次数

			// 显示随机数串
			printf("\n\n按下Enter键开始出题...");
			getchar();
			system("cls");
			seed = time(NULL);
			srand((unsigned)seed);
			printf("\n\n");
			for (i=0; i<sequence_length; i++)
				printf("%d ", rand()%10);

			// 延时对应时长 
			int j;
			for (j = 1;j <= sequence_length;j++);
			Sleep(333);

			// 删除随机数串
			printf("\r");
			for (i=0; i<sequence_length; i++)
				printf("  ");

			do
			{
				correct = 1;
				fflush(stdin);

				// 提示用户输入数串
				printf("\n\n你还有 %d 次机会\n", 3-try_count);
				printf("输入刚才出现的数串，\n"
					   "共 %d 个数字（用空格隔开）：\n", sequence_length);

				// 检查用户输入的是否正确
				srand((unsigned)seed);
				for (i=0; i<sequence_length; i++)
				{
					int n;
					scanf("%d", &n);
					if (n==rand()%10)
						continue;

					correct = 0;
				}

				try_count++;

				if (correct)
				{
					printf("\nCorrect!\n");
					correct_count++;
					sequence_length++;
				}
				else
					printf("\nError!\n");
			} while (!correct && try_count<3);

			fflush(stdin);
		} while (correct == 1);

		time_taken = (clock()-time_taken)/CLOCKS_PER_SEC;

		// 显示一次游戏的分数
		printf("\n\n答对次数： %d\n所用时间：%d (s)\n", correct_count, time_taken);
		printf("\n\n本次测试的得分为 %d\n\n\n", correct_count*100/time_taken);

		// 一次游戏结束，询问是否再玩一次
		printf("是否再玩一次？(y/n)");
		play_again = getchar();
	} while (tolower(play_again) == 'y');

	return 0;
}

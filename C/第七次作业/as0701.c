#include <stdio.h>
/*
统计英文大写字母、小写字母、数字、空格以及其他字符的个数 
*/ 
int main()
{
	char a[3][80],ch;
	int i,j,capital = 0,lowercase = 0,digital = 0,blank = 0,others = 0;
	for(i = 0;i < 3;i++)
	{
		printf("请输入文章第%d行的80个字符：",i + 1);
		j = 0;
		while(j < 80)
		{
			ch = getchar();
			if(ch == '\n')
				continue;
			a[i][j] = ch;
			
			if(a[i][j] == ' ')
				blank += 1;
			else if(a[i][j] >= 'A' && a[i][j] <= 'Z')
				capital += 1;
			else if(a[i][j] >= 'a' && a[i][j] <= 'z')
				lowercase += 1;
			else if(a[i][j] >= '0' && a[i][j] <= '9')
				digital += 1;
			else
				others += 1;
			j += 1; 
		}
	}
	printf("英文大写字母个数：%d\n",capital);
	printf("英文小写字母个数：%d\n",lowercase);
	printf("数字个数：%d\n",digital);
	printf("空格个数：%d\n",blank);
	printf("其他字符个数：%d\n",others);
	return 0 ;    
}

#include <stdio.h>
/*
输入一个句子，将句中每个单词的首字母改为大写，单词之间用空格分隔 
*/
int main()
{
	char str[80],*p;
	int word = 0;
	printf("请输入英文句子:");
	gets(str);
	p = str;
	while(*p != '\0')
	{
		if(*p == ' ')
			word = 0;
		else
			if(word == 0)
			{
				word = 1;
				*p = *p >= 'a' && *p <= 'z'? *p - 32 : *p; 
			}
		p++;
	}
	printf("经过处理的英文句子:%s\n",str);
	return 0 ;
}

#include <stdio.h>
#include <string.h>
/*
任意输入一个字符串，利用strcpy函数和strlen函数删除字符串头部和尾部的空格，
输出处理前和处理后的字符串内容及其长度 
*/
int main()
{
	char str[80],*s,*p;
	printf("请输入原始字符串：");
	gets(str);
	printf("原始字符串长度为%d\n",strlen(str));
	
	s = str;
	while(*s == ' ')
		s++;
	p = str + strlen(str) - 1;
	while(p >= str && *p == ' ')
		p--;
	
	if(p <s)
		*str = '\0';
	else
	{
		size_t len = p - s + 1; 
        strncpy(str, s, len);
        str[len] = '\0';
	}
	
	printf("结果字符串：");
	puts(str);
	printf("结果字符串长度为%d\n",strlen(str)); 
	return 0 ;
} 

#include <stdio.h>

int stringlen(char *str)
{
	int len = 0;
	while(*str != '\0')
	{
		len += 1;
		str++;
	}
	return len;
}
/*
int main()
{
	char str1[] = "abcdefg";
	printf("length = %d",stringlen(str1));
	return 0;
}
*/
/*
int main()
{
	char text[] = "python is an useful language.";
	int len = stringlen(text);
	char up_text[len];
	int i,word = 0;

	for(i = 0;i <= len;i++)
	{
		if(text[i] >= 'A' && text[i] <= 'Z' || text[i] >= 'a' && text[i] <= 'z')
		{
			if(word == 0)
			{
				word = 1;
				up_text[i] = text[i] - 32;
			}
			else
			{
				up_text[i] = text[i];
			}
		}
		else
		{
			word = 0;
			up_text[i] = text[i];
		}
	}
	
	puts(up_text);
	return 0 ;
}
*/

struct stat{
	float max,min,ave
};

struct stat describe(float alist[],int n)
{
	float s = 0,max_v = alist[0],min_v = alist[0];
	int i;
	struct stat desc_v;
	for(i = 0;i < n;i++)
	{
		if (alist[i]>max_v) max_v = alist[i];
		if (alist[i]<min_v) min_v = alist[i];
		s+=alist[i];
	}
	desc_v.max = max_v;
	desc_v.min = min_v;
	desc_v.ave = s / n;
	return desc_v;
}

void show(struct student s)
{
	printf("no: %s\nname: %s\nscores: ",s.no,s.name);
	for(i = 0;i < 5;i++)
	{
		printf("5.1f",s.scores[i]);
	}
}




int main()
{
	
}



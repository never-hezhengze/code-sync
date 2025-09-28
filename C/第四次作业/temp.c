#include <stdio.h>

int main()
{
	int i = 10;
	char seat[100], isseat[20];
	
	isseat[0] = sprintf(seat, "¡¾%d¡¿", i);
	printf("%s", seat);
	printf("%s", isseat[0]);
	return 0 ;
} 

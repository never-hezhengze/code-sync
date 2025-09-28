//打印风寒指数
#include <stdio.h>
#include <math.h>

int main()
{
	int speed = -5;
	float temperature = -20.00,factor;
	
	for (speed;speed <= 50;speed += 5)
	{
		if (speed == -5)
			printf("%-8c",' ');
		else
			printf("%-8d",speed);
		for (temperature = -20;temperature <= 60;temperature += 10)
		{
			if (speed == -5)
				printf("%-8.2f",temperature);
			else if (speed == 0)
				printf("%-8c",'-');
			else
			{
				factor = 35.74 + 0.6215 * temperature - 35.75 * pow(speed,0.16) + 0.4275 * temperature * pow(speed,0.16);
				printf("%-8.2f",factor);
			}
		}
		printf("\n");
	}	
		
	return 0 ;
} 

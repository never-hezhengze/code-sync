//计算本息 
#include <stdio.h> 
#include <math.h>

int main()
{
	double original_money = 8000, sum_money;					
	int year = 1;
	
	for(year = 1;year <= 10;year++)						//计算第一至十年间每年连本带息的金额数， 
	{													//当大于等于10000时跳出循环 
		if(year <= 3)
			sum_money = original_money * pow(1 + 0.028, year);
		else
			sum_money = original_money * pow(1 + 0.028, 3) * pow(1 + 0.027, (year - 3));
		if(sum_money >= 10000)
				break;
	}
	
	printf("用户将在第%d年取出，取出时连本带息是%.2lf元", year, sum_money);
	
	return 0 ;
}

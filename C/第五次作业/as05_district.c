#include <stdio.h>
#include "as05_utility.h"

int main()
{
	float data[5][12] = {{12.3, 15.6, 18.9, 20.1, 22.4, 25.7, 28.9, 27.6, 24.3, 20.1, 16.5, 13.2},
	                     {5.6, 8.9, 11.2, 13.4, 16.7, 19.8, 23.1, 22.3, 19.5, 15.7, 11.9, 8.2},
						 {-3.4, 0.1, 4.5, 7.8, 10.2, 14.5, 18.7, 17.9, 14.6, 10.8, 7.0, 3.3},
						 {8.5, 11.7, 14.9, 16.2, 18.5, 21.8, 25.0, 24.2, 21.5, 17.7, 13.9, 10.2},
						 {2.3, 5.6, 8.9, 10.2, 12.5, 15.8, 19.0, 18.2, 15.9, 12.1, 8.3, 4.6}};
	float ave_year[5];
	int max_month_key[5],min_month_key[5];
	float max_month_value[5],min_month_value[5];
	int max_year,min_year,max_month_city,min_month_city;
	int i;
	
	for (i = 0;i < 5;i++)
	{
		ave_year[i] = AverageTemp(data[i],12);      //保存每个城市的年平均气温 
		max_month_key[i] = MaxTemp(data[i],12);     //保存每个城市12个月中温度最高的月份的索引 
		min_month_key[i] = MinTemp(data[i],12);     //保存每个城市12个月中温度最低的月份的索引 
		max_month_value[i] = data[i][max_month_key[i]];     //对应的具体数值，用于比较大小 
		min_month_value[i] = data[i][min_month_key[i]];
	}
	
	max_year = MaxTemp(ave_year,5);
	min_year = MinTemp(ave_year,5);
	
	max_month_city = MaxTemp(max_month_value,5);
	min_month_city = MinTemp(min_month_value,5);
	
	printf("年平均气温最高的城市是第%d个城市，年平均气温最低的城市是第%d个城市\n",max_year+1,min_year+1);
	printf("月平均气温最高的城市是第%d个城市的第%d月，月平均气温最低的第%d个城市的第%d月\n",max_month_city+1,max_month_key[max_month_city]+1,min_month_city+1,min_month_key[min_month_city]+1);
	
	return 0;
}

#include <stdio.h>
/*
从键盘输入十本书的名称和定价，按书的定价由低到高的顺序输出所有书的各项数据 
*/

struct book{
	float price;
	char name[20];
}; 
int main()
{
	struct book books[10];
	int i, j;

    // 输入书名和价格
    for (i = 0; i < 10; i++) {
        printf("请输入第 %d 本书的名称: ", i + 1);
        scanf("%s", books[i].name);
        printf("请输入第 %d 本书的定价: ", i + 1);
        scanf("%f", &books[i].price);
    }
    // 排序 
    for (i = 0; i < 9; i++) {
        for (j = 0; j < 9 - i; j++) {
            if (books[j].price > books[j + 1].price) {
                struct book temp = books[j];
                books[j] = books[j + 1];
                books[j + 1] = temp;
            }
        }
    }
    printf("\n按价格从低到高排序后的图书信息:\n");
    for (i = 0; i < 10; i++) {
        printf("书名: %-20s 价格: %.2f\n", books[i].name, books[i].price);
    }

    return 0;
} 

#include <stdio.h>
/*
处理字符串中除字母和数字以外的其他ASCII码字符，
对于多于一个的连续相同字符，将其缩减至仅保留一个 
*/

// 判断是否是字母或数字
int isLetterOrDigit(char c) {
    return ((c >= 'a' && c <= 'z') ||
            (c >= 'A' && c <= 'Z') ||
            (c >= '0' && c <= '9'));
}

// 处理字符串：缩减连续的特殊字符，只保留一个
void processString(char str[]) {
    int read = 0, write = 0;
    char prev = '\0';

    while (str[read] != '\0') {
        char current = str[read];

        if (isLetterOrDigit(current)) {
            // 字母或数字，全部保留
            str[write++] = current;
            prev = '\0'; // 重置 prev，避免影响下一个特殊字符
        } else {
            // 是特殊字符
            if (current != prev) {
                str[write++] = current; // 和上一个不一样，就保留
                prev = current;
            }
        }

        read++;
    }

    str[write] = '\0'; // 加结束符
}

int main() {
    char str[100] = "aa##bb!!!cc1122@@@dd";

    printf("原始字符串: %s\n", str);
    processString(str);
    printf("处理后的字符串: %s\n", str);

    return 0;
}


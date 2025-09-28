#include "judgement.h"
#include <stdio.h>

int main() {
    int checkerboard[15][15] = {0};
    int len = 15; // 假设棋盘大小为15x15
    int new_chessman_x = 7;
    int new_chessman_y = 7;

    // 假设在棋盘上放置了一些棋子
    checkerboard[7][7] = 2;
    checkerboard[6][7] = 2;
    checkerboard[5][7] = 2;
    checkerboard[4][7] = 2;
    checkerboard[3][7] = 2;

    int result = Judgement(checkerboard, len, new_chessman_x, new_chessman_y);
    if (result == 1) {
        printf("黑子获胜！\n");
    } else if (result == 2) {
        printf("白子获胜！\n");
    } else {
        printf("游戏未结束！\n");
    }
    return 0;
}

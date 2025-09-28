#include <stdio.h>

/*
将两个升序数组合并为一个升序数组，
合并结果存放在第一个数组中 
*/
void combine(float arr1[], float arr2[], int size1, int size2);
void upsort(float *arr, int size);

int main()
{
    float arr1[15] = {5.3, 29.7, 119.4, 43.9, 30.6};
    float arr2[5] = {57.7, 21.0, 12.5, 94.8, 55.6};
    int i;
    
    upsort(arr1, 5); // 对 arr1 排序
    upsort(arr2, 5); // 对 arr2 排序
    
    combine(arr1, arr2, 5, 5); // 合并 arr2 到 arr1
    
    upsort(arr1, 10); // 对合并后的 arr1 排序
    
    printf("合并并排序后的数组：\n");
    for (i = 0; i < 10; i++)
    {
        printf("%.1f ", arr1[i]);
    }
    printf("\n");
    
    return 0;
}

// 合并两个数组，将 arr2 的元素添加在 arr1 中
void combine(float arr1[], float arr2[], int size1, int size2)
{
    int i;
    for (i = 0; i < size2; i++)
    {
        arr1[size1 + i] = arr2[i];
    }
}

// 将数组 arr 以升序排列，使用冒泡排序
void upsort(float *arr, int size)
{
    int i, j;
    float temp;
    for (i = 0; i < size - 1; i++) // 外层循环控制排序的轮数
    {
        for (j = 0; j < size - i - 1; j++) // 内层循环进行相邻元素的比较和交换
        {
            if (arr[j] > arr[j + 1]) // 如果前一个元素大于后一个元素，则交换
            {
                temp = arr[j];
                arr[j] = arr[j + 1];
                arr[j + 1] = temp;
            }
        }
    }
}

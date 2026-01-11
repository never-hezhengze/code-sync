#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <string>
#include <cstdlib>
#include <ctime>
using namespace std;

// 分区函数
int partition(vector<int>& arr, int low, int high) {
    int random = low + rand() % (high - low + 1);
    swap(arr[random], arr[high]);
    
    int pivot = arr[high];
    int i = low - 1;
    
    for (int j = low; j < high; j++) {
        if (arr[j] < pivot) {
            i++;
            swap(arr[i], arr[j]);
        }
    }
    swap(arr[i + 1], arr[high]);
    return i + 1;
}

// 快速排序
void quickSort(vector<int>& arr, int low, int high) {
    if (low < high) {
        int pi = partition(arr, low, high);
        quickSort(arr, low, pi - 1);
        quickSort(arr, pi + 1, high);
    }
}

int main() {
    srand(time(0));
    
    // 从文件读取输入
    ifstream infile("in.txt");
    if (!infile) {
        cerr << "无法打开输入文件 in.txt" << endl;
        return 1;
    }
    
    string line;
    getline(infile, line);
    infile.close();
    
    stringstream ss(line);
    vector<int> arr;
    int num;
    
    while (ss >> num) {
        arr.push_back(num);
    }
    
    int n = arr.size();
    
    if (n > 0) {
        quickSort(arr, 0, n - 1);
    }
    
    // 输出到文件
    ofstream outfile("out.txt");
    if (!outfile) {
        cerr << "无法打开输出文件 out.txt" << endl;
        return 1;
    }
    
    for (int i = 0; i < n; i++) {
        outfile << arr[i];
        if (i < n - 1) {
            outfile << " ";
        }
    }
    outfile.close();
    
    return 0;
}
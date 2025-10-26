#include <iostream>
using namespace std;

// 循环队列类
class CircularQueue {
private:
    int* data;
    int front, rear;
    int capacity;
public:
    CircularQueue(int size) {
        capacity = size + 1;
        data = new int[capacity];
        front = rear = 0;
    }
    ~CircularQueue() {
        delete[] data;
    }
    bool enqueue(int x) {
        if ((rear + 1) % capacity == front) return false;
        data[rear] = x;
        rear = (rear + 1) % capacity;
        return true;
    }
    bool dequeue(int& x) {
        if (front == rear) return false;
        x = data[front];
        front = (front + 1) % capacity;
        return true;
    }
    bool isEmpty() {
        return front == rear;
    }
};

int main() {
    int n;
    cin >> n;

    CircularQueue q(n + 2); // 队列容量足够

    // 第一行
    cout << "1" << endl;
    q.enqueue(1);
    q.enqueue(0); // 行结束标志

    // 生成第2到n行
    for (int i = 2; i <= n; i++) {
        int a, b;
        // 行首固定1
        cout << "1 ";
        q.enqueue(1);

        q.dequeue(a);
        while (true) {
            q.dequeue(b);
            if (b == 0) {
                // 上一行结束
                cout << "1" << endl;
                q.enqueue(1);
                q.enqueue(0);
                break;
            } else {
                int sum = a + b;
                cout << sum << " ";
                q.enqueue(sum);
                a = b;
            }
        }
    }

    return 0;
}

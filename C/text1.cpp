#include <iostream>
using namespace std;

// 链表节点定义
struct ListNode
{
    int val;
    ListNode *next;
    ListNode(int x) : val(x), next(nullptr) {}
};

// 链表类
class LinkedList
{
private:
    ListNode *head;

public:
    LinkedList() : head(nullptr) {}

    // 从数组构建链表
    void createFromArray(int arr[], int n)
    {
        if (n == 0)
            return;

        head = new ListNode(arr[0]);
        ListNode *current = head;

        for (int i = 1; i < n; i++)
        {
            current->next = new ListNode(arr[i]);
            current = current->next;
        }
    }

    // 获取头节点
    ListNode *getHead() const
    {
        return head;
    }

    // 在链表头部插入节点（用于构建递减序列）
    void insertAtHead(int val)
    {
        ListNode *newNode = new ListNode(val);
        newNode->next = head;
        head = newNode;
    }

    // 打印链表
    void printList() const
    {
        ListNode *current = head;
        while (current)
        {
            cout << current->val;
            if (current->next)
                cout << " ";
            current = current->next;
        }
    }

    // 析构函数释放内存
    ~LinkedList()
    {
        ListNode *current = head;
        while (current)
        {
            ListNode *temp = current;
            current = current->next;
            delete temp;
        }
    }
};

// 归并两个递增链表，得到递减链表（去除重复元素）
LinkedList mergeToDescending(ListNode *headA, ListNode *headB)
{
    LinkedList result;
    ListNode *p = headA;
    ListNode *q = headB;

    int lastValue = -1; // 记录上一个插入的值，用于去重

    // 使用头插法，同时遍历两个链表
    while (p && q)
    {
        if (p->val <= q->val)
        {
            // 只有当当前值不等于上一个插入的值时才插入（去重）
            if (result.getHead() == nullptr || p->val != lastValue)
            {
                result.insertAtHead(p->val);
                lastValue = p->val;
            }
            p = p->next;
        }
        else
        {
            // 只有当当前值不等于上一个插入的值时才插入（去重）
            if (result.getHead() == nullptr || q->val != lastValue)
            {
                result.insertAtHead(q->val);
                lastValue = q->val;
            }
            q = q->next;
        }
    }

    // 处理链表A的剩余节点
    while (p)
    {
        if (result.getHead() == nullptr || p->val != lastValue)
        {
            result.insertAtHead(p->val);
            lastValue = p->val;
        }
        p = p->next;
    }

    // 处理链表B的剩余节点
    while (q)
    {
        if (result.getHead() == nullptr || q->val != lastValue)
        {
            result.insertAtHead(q->val);
            lastValue = q->val;
        }
        q = q->next;
    }

    return result;
}

int main()
{
    const int MAX_SIZE = 100;
    int arrA[MAX_SIZE], arrB[MAX_SIZE];
    int countA = 0, countB = 0;

    // 读取第一行输入（链表A）
    int num;
    while (cin >> num)
    {
        arrA[countA++] = num;
        if (cin.get() == '\n')
            break;
    }

    // 读取第二行输入（链表B）
    while (cin >> num)
    {
        arrB[countB++] = num;
        if (cin.get() == '\n')
            break;
    }

    // 创建链表A和B
    LinkedList listA, listB;
    listA.createFromArray(arrA, countA);
    listB.createFromArray(arrB, countB);

    // 归并得到递减链表C（去除重复）
    LinkedList listC = mergeToDescending(listA.getHead(), listB.getHead());

    // 输出结果
    listC.printList();

    return 0;
}
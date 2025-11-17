#include <iostream>
#include <string>
#include <unordered_map>
#include <queue>
using namespace std;

// 二叉树节点结构
struct TreeNode {
    char val;
    TreeNode* left;
    TreeNode* right;
    TreeNode(char x) : val(x), left(nullptr), right(nullptr) {}
};

// 构建二叉树
TreeNode* buildTree(unordered_map<char, pair<char, char>>& nodes, char rootVal) {
    if (rootVal == '#') return nullptr;
    
    TreeNode* root = new TreeNode(rootVal);
    
    // 构建左子树
    char leftVal = nodes[rootVal].first;
    root->left = buildTree(nodes, leftVal);
    
    // 构建右子树
    char rightVal = nodes[rootVal].second;
    root->right = buildTree(nodes, rightVal);
    
    return root;
}

// 使用BFS查找值为x的结点所在的最小层次
int findMinLevel(TreeNode* root, char x) {
    if (root == nullptr) return -1;
    
    queue<pair<TreeNode*, int>> q;  // 存储节点和对应的层次
    q.push({root, 1});
    
    while (!q.empty()) {
        TreeNode* node = q.front().first;
        int level = q.front().second;
        q.pop();
        
        // 如果找到目标节点，返回当前层次
        if (node->val == x) {
            return level;
        }
        
        // 将左右子节点加入队列
        if (node->left != nullptr) {
            q.push({node->left, level + 1});
        }
        if (node->right != nullptr) {
            q.push({node->right, level + 1});
        }
    }
    
    return -1;  // 没有找到
}

int main() {
    int n;
    cin >> n;
    
    unordered_map<char, pair<char, char>> nodes;
    char rootVal = ' ';
    
    // 读取节点信息
    for (int i = 0; i < n; i++) {
        char parent, left, right;
        cin >> parent >> left >> right;
        
        nodes[parent] = make_pair(left, right);
        
        // 第一个节点作为根节点
        if (i == 0) {
            rootVal = parent;
        }
    }
    
    // 读取要查找的目标值
    char x;
    cin >> x;
    
    // 构建二叉树
    TreeNode* root = buildTree(nodes, rootVal);
    
    // 查找并输出最小层次
    int minLevel = findMinLevel(root, x);
    cout << minLevel << endl;
    
    return 0;
}
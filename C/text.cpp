#include <iostream>
#include <vector>
using namespace std;

vector<vector<int>> graph;
vector<int> path;
vector<bool> visited;
int n, m, u, v, w;
bool found = false;

void dfs(int cur) {
    if (cur == w) return; // 不能经过 w
    if (cur == v) {
        // 输出路径
        for (size_t i = 0; i < path.size(); i++) {
            cout << path[i];
            if (i != path.size() - 1) cout << " ";
        }
        cout << endl;
        found = true;
        return;
    }
    
    for (int next : graph[cur]) {
        if (!visited[next] && next != w) {
            visited[next] = true;
            path.push_back(next);
            dfs(next);
            path.pop_back();
            visited[next] = false;
        }
    }
}

int main() {
    cin >> n >> m >> u >> v >> w;
    graph.resize(n);
    visited.resize(n, false);
    
    for (int i = 0; i < m; i++) {
        int a, b;
        cin >> a >> b;
        graph[a].push_back(b);
    }
    
    // 如果起点或终点就是 w，直接无解
    if (u == w || v == w) {
        cout << -1 << endl;
        return 0;
    }
    
    visited[u] = true;
    path.push_back(u);
    dfs(u);
    
    if (!found) {
        cout << -1 << endl;
    }
    
    return 0;
}
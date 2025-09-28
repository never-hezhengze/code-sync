#include <iostream>

int main()
{
	std::cout << "这是 C++ 程序" << std::endl;
#ifdef __cplusplus
	std::cout << "正确：被当作 C++ 编译了" << std::endl;
#else
	std::cout << "错误：被当作 C 编译了" << std::endl;
#endif
	return 0;
}
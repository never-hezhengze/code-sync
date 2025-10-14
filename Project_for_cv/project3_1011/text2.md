**平移**：
\[T = 
\left( \begin{array}{ccc}
1 & 0 & t_{x} \\
0 & 1 & t_{y} \\
0 & 0 & 1
\end{array} \right)
\]
- 待求元素：$t_x,t_y$
- 合理取值范围：$R$

**缩放**：
\[S = 
\left( \begin{array}{ccc}
s_x & 0 & 0\\
0 & s_y & 0\\
0 & 0 & 1
\end{array}\right)
\]
- 待求元素：$s_x,s_y$
- 合理取值范围：$s_x,s_y >0$
- $s_x,s_y >1$时放大，$s_x,s_y <1$时缩小

**旋转**：
\[R = 
\left( \begin{array}{ccc}
cos\theta & -sin\theta & 0\\
sin\theta & cos\theta & 0\\
0 & 0 & 1
\end{array}\right)
\]
- 待求元素：$\theta$
- 合理取值范围：$[0,2\pi)$

### 如何确定这些元素：
<span style="color:rgba(199, 0, 0, 1)">根据点对匹配</span>
在图像A和B中找匹配点
**对于纯平移**：只需要一对匹配点，$t_x=x'-x,t_y=y'-y$
**对于纯缩放**：只需要一对匹配点，$s_x=\frac{x'}{x},s_y=\frac{y'}{y}$
如果缩放中心未知，则需要两对匹配点
**对于纯旋转**：只需要一对匹配点，$\theta=arctan\frac{xy'-yx'}{xx'+yy'}$


function z=lagrint(x,y,x0)
    %计算x0处的插值函数L(x)的值
% @param [in] x: 插值点的x坐标
% @param [in] y: 插值点的y坐标
% @param [in] x0: 要计算x0处的函数值L(x0), 现在的x0是1x1 double, 后续
%         希望能改成x0 可以是 1xn 的矩阵
% @param [out] z: 返回值z=L(x0)


n=length(x);
l=ones(1,n);
omega_x = x0 - x;  
for i=1:n
    	x_ij = x(i)- x; 
    	if i == 1
    			l(i) = prod(omega_x(i+1:n)) / prod(x_ij(i+1:n));
    	elseif i == n
    l(i) = prod(omega_x(1:i-1)) / prod(x_ij(1:i-1));
    		else
    			l(i) = prod(omega_x(1:i-1)) / prod(x_ij(1:i-1));
    			l(i) = l(i)*prod(omega_x(i+1:n)) / prod(x_ij(i+1:n));
    		end
end
z=y*l';
end


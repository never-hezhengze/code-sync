function [c,err,yc] = bisect(f,a,b,delta)
    %输入    ——  f 输入函数句柄
    %       ——  a,b 初始区间的左右边界
    %       ——  delta 为容差
    %输出   —— c 为近似零点
    %       —— yc = f(c)
    %       —— err 为 c 的误差估计
    
    ya = f(a);
    yb = f(b);
    if ya*yb > 0
        warning("请输入合适的区间。");
        return 
    end
    max1 = 1+round((log(b-a)-log(delta))/log(2));
    for k = 1:max1
        c = (a+b)/2;
        yc = f(c);
        if yc == 0
            a = c;
            b=c;
        elseif yb*yc > 0
            b = c;
            yb = yc;
        else
            a = c;
            ya = yc;
        end
        if b-a < delta
            break;
        end
    end
    c = (a+b)/2;
    err = abs(b-a);
    yc = f(c);
            
    
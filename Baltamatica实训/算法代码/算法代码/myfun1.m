function [y] = myfun1(x)
    
    if x<=0
        y = sin(x);
    elseif x<=3
        y = x;
    else
        y = -x+6;
    end
end
    
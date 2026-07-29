load("春运人数统计.mat");
t = tp(7:end-2,1);
lnp =log10(tp(7:end-2,2));

拟合多项式 = polyfit(t,lnp, 2);
x=t(1):1:2030;
y = polyval(拟合多项式,x);
plot(x,y,'-r*')

plot(tp(7:end,1), tp(7:end,2), 'bo', x, 10.^y, '-r*')
legend('统计数据','拟合数据')
title("春运人数") 
ylabel("人口:亿")
xlabel("年")
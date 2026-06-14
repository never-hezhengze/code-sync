data.outline=function(x)
  ## input ###################
  ## x = a vector ############
  ## output ##################
  ## the outline of data x ###
{  
   n  = length(x)     # 计算长度

   m  = mean(x)       # 均值
   v  = var(x)        # 样本方差
   s  = sd(x)         # 样本标准差
   me = median(x)     # 中位数
   
   
   m1 = min(x)        # 最小值
   m2 = max(x)        # 最大值
   Q1 = quantile(x, 1/4)       # 上四分位数
   Q3 = quantile(x, 3/4)       # 下四分位数
   
   R  = m2-m1         # 极差   
   R1 = Q3-Q1         # 四分位距
   
   cv   = s/m         # 变异系数
   skew = sum((x-m)^3/s^3)/n         # 偏度
   kurt = sum((x-m)^4/s^4)/n-3       # 超额峰度
   
   return(list(size=n, Mean=m, Var=v, Std=s, Median=me, 
               Min=m1, Max=m2, Q1=Q1, Q3=Q3, R=R, R1=R1, 
               CV=cv, Skew=skew, kurtosis=kurt))
}


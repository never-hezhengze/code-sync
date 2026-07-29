load_plugin('dip'); % 加载图像处理工具箱
A = imread('原图像.jpg'); %使用imread函数导入图像数据
A = rgb2gray(A);
A = dipmat2bxmat(im2double(A));
imagesc(A)  % 显示图像
colormap(gray);title('原始图像')
A=double(A); %将图像数据从 uint8(无符号8位整数)转换为double
[U S V]=svd(A);
rank(A)
%%
figure(2);
k =  125; % 取前 125 个奇异值
Aapprox125 = U(:,1:k)*S(1:k,1:k)*V(:,1:k)';
imagesc(Aapprox125);colormap(gray);title('图像1')

figure(3);
k =  225; % 取前 225 个奇异值
Aapprox225 = U(:,1:k)*S(1:k,1:k)*V(:,1:k)';
imagesc(Aapprox225);colormap(gray);title('图像2')





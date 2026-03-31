clc; clear; close all;

U = linspace(0.01, 3, 400); % 避开0
I = 0.01 * (exp(2 * U) - 1);

figure;
semilogy(U, I, 'k', 'LineWidth', 2);

xlabel('U');
ylabel('I (log scale)');
title('LED 正向伏安特性（半对数）');

grid on;
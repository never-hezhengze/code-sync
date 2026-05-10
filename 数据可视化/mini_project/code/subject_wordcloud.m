clc; clear; close all;

subjects = [
    "Artificial intelligence"
    "Machine learning"
    "Computational intelligence"
    "Educational research"
    "Technological innovation"
    "Knowledge and innovation"
    "Internet of things"
    "Data analysis and big data"
    "Data mining"
    "Cloud computing"
    "Smart infrastructure"
    "Knowledge based systems"
    "Internet of things applications in smart environments"
    "Philosophy of artificial intelligence"
    "Education science"
];

counts = [9384 7921 6170 5403 4963 4685 4346 ...
          4082 4039 3904 3816 3616 3558 3523 3518];

figure;
wordcloud(subjects, counts);
title('Springer相关主题文字云图');
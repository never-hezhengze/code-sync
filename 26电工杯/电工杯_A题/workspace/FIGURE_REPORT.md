# 图表生成报告

## 生成概况

共生成 **14 张** 学术级 PDF 图表，覆盖问题一至问题五全部规划图表。

## 图表清单

| 编号 | 文件名 | 图表类型 | 内容 | 章节 |
|------|--------|---------|------|------|
| 1 | fig_q1_power_balance.pdf | 面积图 | 典型日功率平衡曲线 | 问题一 |
| 2 | fig_q1_indicators.pdf | 分组柱状图 | 三项绿电指标与阈值对比 | 问题一 |
| 3 | fig_q2_cost_vs_production.pdf | 折线图 | 不同日产量下吨氨成本 | 问题二(1) |
| 4 | fig_q2_schedule_gantt.pdf | 甘特图 | 各产量24h开停机安排 | 问题二(1) |
| 5 | fig_q2_scenarios_heatmap.pdf | 热力图 | 24场景吨氨成本矩阵 | 问题二(2) |
| 6 | fig_q2_annual_cost.pdf | 面积图 | 全年吨氨成本分布 | 问题二(2) |
| 7 | fig_q2_green_indicators.pdf | 堆叠柱状图 | 绿电指标满足情况统计 | 问题二(2) |
| 8 | fig_q3_dispatch.pdf | 双轴图 | 连续调度功率曲线 | 问题三(1) |
| 9 | fig_q3_annual_cost.pdf | 折线图 | 全年成本分布对比 | 问题三(1) |
| 10 | fig_q3_comparison.pdf | 发散柱状图 | 问题三vs问题二指标变化 | 问题三(3) |
| 11 | fig_q4_offgrid_production.pdf | 分组柱状图 | 24场景离网制氨产量 | 问题四(1) |
| 12 | fig_q4_storage_dispatch.pdf | 面积图 | 储能参与功率调度 | 问题四(2) |
| 13 | fig_q4_economics.pdf | 瀑布图 | 离网vs联网成本分解 | 问题四(3) |
| 14 | fig_q5_radar.pdf | 雷达图 | 绿电园区影响评价 | 问题五 |

## 图表多样性

| 图表类型 | 使用次数 |
|---------|---------|
| 面积图 | 3 |
| 折线图 | 2 |
| 分组柱状图 | 2 |
| 甘特图 | 1 |
| 热力图 | 1 |
| 堆叠柱状图 | 1 |
| 双轴图 | 1 |
| 发散柱状图 | 1 |
| 瀑布图 | 1 |
| 雷达图 | 1 |

## 风格说明

- 配色方案: SciencePlots (science) + 自定义学术配色
- 字体: SimHei (中文) + Arial (英文/数字)
- 输出格式: PDF (矢量, 300 DPI)
- 所有图表无标题 (标题在 LaTeX caption 中)
- 去除顶部和右侧边框
- 中文标签和图例

## LaTeX 引用

已生成 `figures/latex_includes.tex`，在论文主文件中使用：
```latex
\input{figures/latex_includes.tex}
```

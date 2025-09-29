import pandas as pd
# 读取数据
data = pd.read_csv("C:\\Users\\贺正泽\\Desktop\\data\\Wimbledon_featured_matches.csv")
# 添加一列表示比赛积分状态（包括局分和盘分）
data['score_status'] = data['p1_games'].astype(str) + '-' + data['p2_games'].astype(str) + ' ' + data['p1_sets'].astype(str) + '-' + data['p2_sets'].astype(str)

# 只分析第一场比赛
match_1 = data.iloc[0]['match_id']
df = data[data['match_id'] == match_1]
player1 = data.iloc[0]['player1']
player2 = data.iloc[0]['player2']

def build_transition_matrix(df_):
    transition_matrix2 = {}
    for i in range(len(df_) - 1):
        row = df_.iloc[i]
        next_row = df_.iloc[i + 1]
        current_state = (row['player1'], row['score_status'], row['server'])
        next_state = (next_row['player1'], next_row['score_status'], next_row['server'])
        if current_state not in transition_matrix2:
            transition_matrix2[current_state] = {}
        if next_state not in transition_matrix2[current_state]:
            transition_matrix2[current_state][next_state] = 0
        transition_matrix2[current_state][next_state] += 1
    return transition_matrix2

def normalize_transition_matrix(transition_matrix_):
    for current_state, next_states in transition_matrix_.items():
        total_transitions_ = sum(next_states.values())
        for next_state in next_states:
            transition_matrix[current_state][next_state] /= total_transitions_
    return transition_matrix_

transition_matrix = build_transition_matrix(df)
transition_matrix = normalize_transition_matrix(transition_matrix)

def serving_advantage(server):
    if server == 1:
        return 0.6  
    else:
        return 0.4  

def calculate_win_prob(transition_matrix1):
    win_prob1 = {}
    for state in transition_matrix1:
        if state not in win_prob1.keys():
            win_prob1[state] = 0
        for next_state, prob in transition_matrix1[state].items():
            win_prob1[state] += prob * serving_advantage(state[2])
    return win_prob1

win_prob = calculate_win_prob(transition_matrix)

import matplotlib.pyplot as plt
import numpy as np

def visualize_match_flow(win_prob1, df1):
    x = np.arange(len(df1))
    y_p1 = [win_prob1[(df1.iloc[i]['player1'], df1.iloc[i]['score_status'], df1.iloc[i]['server'])] for i in range(len(df))]
    y_p2 = [1 - win_prob1[(df1.iloc[i]['player1'], df1.iloc[i]['score_status'], df1.iloc[i]['server'])] for i in range(len(df))]
    plt.figure(figsize=(10, 5))
    plt.plot(x, y_p1, color='red', label=player1)
    plt.plot(x, y_p2, color='blue', label=player2)
    plt.xlabel('Point Number')
    plt.ylabel('Win Probability')
    plt.title('Match Flow')
    plt.legend()
    plt.show()

visualize_match_flow(win_prob, df)



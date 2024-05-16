"""
强化学习（reinforcement learning，RL）通过从反复试验中不断试错来学习，并根据收
到的奖励和惩罚来更新最佳行动策略。强化学习算法可以用于需要连续采取行动并且立
即获得奖励的环境，比如用于计算机游戏中。

强化学习 demo
"""

import numpy as np

def epoch():
    ssp = [1, 1, 1, 1, 0]
    action = [0, 1]
    tr = 0
    for _ in range(1000):
        a = np.random.choice(action)
        s = np.random.choice(ssp)
        if a == s:
            tr += 1
        action.append(s)
    return tr

def main():
    r = np.array([epoch() for _ in range(15)])
    print(r, r.mean())

if __name__ == "__main__":
    main()
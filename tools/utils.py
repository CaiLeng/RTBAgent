import math
import numpy as np
import pandas as pd
import pulp

def simulate_ad_bidding( clicks, bids, market_prices):
    status = bids >= market_prices
    cost = market_prices * status
    value = clicks * status
    return value, cost, status

def find_w0_star(p_v,c,B,v,c_star=0):
    # traditional optimization approach
    prob = pulp.LpProblem("LP_Problem", pulp.LpMinimize)
    alpha = pulp.LpVariable('alpha', lowBound=0)
    r = {i: pulp.LpVariable(f'r_{i}', lowBound=0) for i in range(len(c))}
    prob += (B - c_star) * alpha + pulp.lpSum(r.values())
    for i in range(len(c)):
        prob += c[i] * alpha + r[i] >= p_v[i]
    prob.solve()
    w_star =  1/ pulp.value(alpha)
    bids = np.array([p_v[i] * w_star for i in range(len(p_v))])
    value, cost, status = simulate_ad_bidding(v, bids, c)
    current_budget = B - c_star
    over_cost_ratio = max((np.sum(cost) - current_budget) / (np.sum(cost) + 1e-4), 0)
    while over_cost_ratio > 0:
        pv_index = np.where(status == 1)[0]
        dropped_pv_index = np.random.choice(pv_index, int(math.ceil(pv_index.shape[0] * over_cost_ratio)),
                                            replace=False)
        bids[dropped_pv_index] = 0
        value, cost, status = simulate_ad_bidding(v, bids, c)
        over_cost_ratio = max((np.sum(cost) - current_budget) / (np.sum(cost) + 1e-4), 0)

    return np.sum(value),w_star


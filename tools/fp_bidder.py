# *_*coding:utf-8 *_*
import json
import os.path

import numpy as np
import pulp
import pandas as pd
from tqdm import tqdm
import  sys
sys.path.append("/path/RTBAgent")
from tools.utils import find_w0_star




def generate_checkpoint():
    data_root = '/path/RTBAgent/ipinyouData/new_all'
    checkpoint_root = '/path/RTBAgent/checkpoint'
    train_data_dfs = {}
    advertiser_ids = os.listdir(data_root)
    advertiser_ids = sorted(advertiser_ids, key=lambda x: int(x))
    for advertiser_id in tqdm(advertiser_ids):
        train_data_pickle_path = os.path.join(data_root, advertiser_id, "train.pickle")
        train_data_df = pd.read_pickle(train_data_pickle_path).sort_values("timestamp")
        train_data_dfs[advertiser_id] = train_data_df
    checkpoints = {}
    optimal_Rs={}
    avg_ctrs ={}
    for advertiser_id in tqdm(advertiser_ids):
        checkpoints[str(advertiser_id)] = {}
        optimal_Rs[str(advertiser_id)] = {}
        for budget_ratio in tqdm([0.5, 0.25, 0.125, 0.0625, 0.03125]):
            train_data:pd.DataFrame = train_data_dfs[advertiser_id]
            data_df = train_data.copy()
            p_pv_value = data_df['pctr'].copy()
            pv_value = data_df['click'].copy()
            total_budget = sum(data_df['payprice'])*budget_ratio
            optimal_R,w_star = find_w0_star( p_pv_value=p_pv_value.values, market_price=data_df['payprice'].values,budget=float(total_budget),pv_value=pv_value.values)
            checkpoints[str(advertiser_id)][str(budget_ratio)] = w_star
            optimal_Rs[str(advertiser_id)][str(budget_ratio)] = optimal_R

            avg_ctr = np.mean(p_pv_value)
            avg_ctrs[str(advertiser_id)] = avg_ctr

    checkpoint_json_path = os.path.join(checkpoint_root, 'bid', 'fp_bid', "checkpoint.json")
    with open(checkpoint_json_path, "w",
              encoding='utf-8') as f:
        f.write(json.dumps(checkpoints, ensure_ascii=False, indent=4))
    optimal_R_json_path = os.path.join(checkpoint_root, 'bid', 'fp_bid', "optimal_R.json")
    with open(optimal_R_json_path, "w",
              encoding='utf-8') as f:
        f.write(json.dumps(optimal_Rs, ensure_ascii=False, indent=4))
    avg_ctr_json_path = os.path.join(checkpoint_root, 'bid', 'fp_bid', "avg_pctr.json")
    with open(avg_ctr_json_path, "w",
              encoding='utf-8') as f:
        f.write(json.dumps(avg_ctrs, ensure_ascii=False, indent=4))


class FpBidder:
    introduction :str = """The concept of FpBidder is It is a bidding method based on linear programming modeling, which solves the problem of maximizing profits under fixed budget constraints and learns optimal parameters from historical data. In the subsequent bidding process, the parameters will be fixed to the calculated optimal value. However, when the online environment is highly dynamic, the effect will be slightly affected."""
    def __init__(self, advertiser_id:str ,budget_ratio:str):
        self.checkpoint_root = '/path/RTBAgent/checkpoint'
        self.json_data_path  = os.path.join(self.checkpoint_root,'bid','fp_bid',"checkpoint.json")
        if os.path.exists(self.json_data_path):
            with open(self.json_data_path, "r", encoding='utf8') as fp:
                self.bidding_factor = json.load(fp)[str(advertiser_id)][budget_ratio]

        self.pctr_json_path  = os.path.join(self.checkpoint_root,'bid','fp_bid',"avg_pctr.json")
        if os.path.exists(self.pctr_json_path):
            with open(self.pctr_json_path, "r", encoding='utf8') as fp:
                self.avg_pctr = json.load(fp)[str(advertiser_id)]

    def get_bidding_factor(self):
        return round(self.bidding_factor,2)

    def get_algorithm_introduction(self):
        return self.introduction

    def get_avg_pctr(self):
        return self.avg_pctr

    def get_bidding_reference(self):
        return "FpBidder Introduction: {introduction} \n" \
               "The reference bidding factor it provides is : {bidding_factor}. ".format(introduction= self.get_algorithm_introduction(),
                                                                                         bidding_factor = self.get_bidding_factor())
if __name__ == '__main__':
    generate_checkpoint()

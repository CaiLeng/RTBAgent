# *_*coding:utf-8 *_*
import os.path
import pandas as pd
from numpy import NaN


class EnvironmentalStatusProvider:
    def __init__(self, advertiser_id: str, workspace_root: str):
        self.advertiser_id = advertiser_id
        self.workspace_root = workspace_root

    def get_environmental_status(self,given_budget,remaining_budget,total_bid_episode_num,remaining_bid_episode_num):
        data_dir = os.path.join(self.workspace_root, "env")
        environment_status = {}
        environment_status['total_bid_episode_num'] = total_bid_episode_num
        environment_status['remaining_bid_episode_num'] = remaining_bid_episode_num
        environment_status['today_given_budget'] = given_budget
        environment_status['today_remaining_budget'] = remaining_budget

        environment_status_text = ""
        for key in environment_status.keys():
            text = "- {key}:{content}\n".format(key=key, content=round(environment_status[key], 5))
            environment_status_text += text

        if os.path.exists(data_dir) is False:
            return environment_status_text

        data_name_list = os.listdir(data_dir)

        if len(data_name_list) == 0:
            return environment_status_text
        else:
            data_dfs = []
            for data_name in data_name_list:
                json_path = os.path.join(data_dir,data_name, "{}.json".format(self.advertiser_id))
                if os.path.exists(json_path):
                    df = pd.read_json(json_path, orient='index').T
                    data_dfs.append(df)
            if len(data_dfs) == 0:
                return environment_status_text

            concat_df = pd.concat(data_dfs)
            concat_df['actual_click_num'] = concat_df['actual_click_rate'] * concat_df['traffic_num']
            concat_df['predict_click_num'] = concat_df['predict_click_rate'] * concat_df['traffic_num']
            concat_df['bid_price_sum'] = concat_df['bid_price_avg'] * concat_df['traffic_num']
            concat_df['market_price_sum'] = concat_df['market_price_avg'] * concat_df['traffic_num']
            concat_df['win_num'] = concat_df['win_rate'] * concat_df['traffic_num']
            concat_df['datetime'] = pd.to_datetime(concat_df['datetime'], format='%Y-%m-%d-%H')

            concat_df_sorted = concat_df.sort_values(by='datetime', ascending=True)
            concat_df_sorted['date'] = concat_df_sorted['datetime'].dt.year
            concat_df_sorted['month'] = concat_df_sorted['datetime'].dt.month
            concat_df_sorted['day'] = concat_df_sorted['datetime'].dt.day
            last_record = concat_df_sorted.iloc[-1]
            concat_df_sorted_filter = concat_df_sorted[ (concat_df_sorted['day'] == last_record['day']) &
                                                        (concat_df_sorted['month'] == last_record['month']) &
                                                        (concat_df_sorted['day'] == last_record['day']) ]
            environment_status['historical_traffic_num'] = concat_df_sorted_filter['traffic_num'].sum()
            environment_status['historical_market_price_avg'] = concat_df_sorted_filter['market_price_sum'].sum() / concat_df_sorted_filter[
                'traffic_num'].sum()
            environment_status['historical_bid_price_avg'] = concat_df_sorted_filter['bid_price_sum'].sum() / concat_df_sorted_filter[
                'traffic_num'].sum()
            environment_status['historical_predict_ctr_avg'] = concat_df_sorted_filter['predict_click_num'].sum() / concat_df_sorted_filter[
                'traffic_num'].sum()
            environment_status['historical_ctr_avg'] = concat_df_sorted_filter['actual_click_num'].sum() / concat_df_sorted_filter[
                'traffic_num'].sum()
            environment_status['historical_win_rate_avg'] = concat_df_sorted_filter['win_num'].sum() / concat_df_sorted_filter['traffic_num'].sum()


        environment_status_text=""
        for key in environment_status.keys():
            if environment_status[key] == NaN:
                environment_status[key] = 0
            text = "- {key}:{content}\n".format(key=key, content=round(environment_status[key],5))
            environment_status_text += text

        return environment_status_text


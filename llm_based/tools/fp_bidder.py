# *_*coding:utf-8 *_*
import json
import os.path

class FpBidder:
    introduction :str = """The concept of FpBidder is It is a bidding method based on linear programming modeling, which solves the problem of maximizing profits under fixed budget constraints and learns optimal parameters from historical data. In the subsequent bidding process, the parameters will be fixed to the calculated optimal value. However, when the online environment is highly dynamic, the effect will be slightly affected."""
    def __init__(self, advertiser_id:str ,budget_ratio:str):
        self.checkpoint_root = '/path/RTBAgent/checkpoint'

        self.json_data_path  = os.path.join(self.checkpoint_root,'bid','fp_bid',"checkpoint.json")
        if os.path.exists(self.json_data_path):
            with open(self.json_data_path, "r", encoding='utf8') as fp:
                self.bidding_factor = json.load(fp)[str(advertiser_id)][budget_ratio]

    def get_bidding_factor(self):
        return round(self.bidding_factor,2)

    def get_algorithm_introduction(self):
        return self.introduction

    def get_bidding_reference(self):
        return "FpBidder Introduction: {introduction} \n" \
               "The reference bidding factor it provides is : {bidding_factor}. ".format(introduction= self.get_algorithm_introduction(),
                                                                                         bidding_factor = self.get_bidding_factor())
if __name__ == '__main__':
    # generate_checkpoint()
    print(FpBidder(advertiser_id='1458',budget_ratio='0.5').get_bidding_reference())
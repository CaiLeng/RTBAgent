# *_*coding:utf-8 *_*
from tools.fp_bidder import FpBidder
from tools.fp_bidder_for_train import FpBidderTrain


class BasicAgent:
    def __init__(self,remaining_budget,budget_ratio,advertiser_id,bidder_name, is_train = True,):

        self.given_budget = remaining_budget
        self.remaining_budget: float = remaining_budget
        self.budget_ratio: str = budget_ratio
        self.min_remaining_budget: float = 0.001
        self.advertiser_id: str = advertiser_id
        self.click_num: float = 0


        self.init_lambda:float = 0
        self.slot_lambda:float = 0
        self.slot_action:float = 0
        self.slot_step :float = 0
        self.slot_num :float = 0


        if  bidder_name == "fp":
            if is_train :
                bidder = FpBidderTrain(advertiser_id=advertiser_id, budget_ratio=budget_ratio)
            else:
                bidder = FpBidder(advertiser_id=advertiser_id, budget_ratio=budget_ratio)


            self.tools = { "bidder": bidder}


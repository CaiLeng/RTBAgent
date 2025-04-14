# *_*coding:utf-8 *_*
import json
import os
from llm_based.actions.output_bidding_strategy import OutputBiddingStrategy
from llm_based.actions.reflect import Reflect
from llm_based.tools.data_analyzer import DataAnalyzer
from llm_based.tools.environmental_status_provider import EnvironmentalStatusProvider
from llm_based.tools.gen_experience_prompt import generate_experience_prompt
from llm_based.tools.fp_bidder import FpBidder
from llm_based.tools.history_summary_provider import HistorySummaryProvider
from metagpt.roles import Role
from tools.fp_bidder_for_train import FpBidderTrain


class RTBAgent(Role):
    advertiser_id: str

    role_prompt: str

    is_train: bool = False

    remaining_budget: float = 0
    budget_ratio: str = "0.5"
    min_remaining_budget: float = 0.001
    given_budget: float = 0
    bid_done: bool = False

    bidder_name: str
    click_num: float = 0

    workspace_root: str

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.completion_tokens = 0
        self.prompt_tokens = 0
        bidder_name = kwargs['bidder_name']
        if bidder_name == "llm_fp":
            if self.is_train:
                bidder = FpBidderTrain(advertiser_id=self.advertiser_id, budget_ratio=self.budget_ratio)
            else:
                bidder = FpBidder(advertiser_id=self.advertiser_id, budget_ratio=self.budget_ratio)
        self.bidder = bidder
        self.data_analyzer = DataAnalyzer()
        self.environment_status_provider = EnvironmentalStatusProvider(
            advertiser_id=self.advertiser_id,
            workspace_root=self.workspace_root
        )
        self.history_summary_provider = HistorySummaryProvider(
            advertiser_id=self.advertiser_id,
            workspace_root=self.workspace_root
        )

    async def get_history_summary(self, action, formatted_time_str):
        history_summary_provider: HistorySummaryProvider = self.history_summary_provider
        return await history_summary_provider.get_history_summary(action=action,
                                                                  formatted_time_str=formatted_time_str)
    def get_environment_status(self, total_bid_episode_num, remaining_bid_episode_num):
        environment_status_provider: EnvironmentalStatusProvider = self.environment_status_provider

        environment_status = environment_status_provider.get_environmental_status(
            given_budget=self.given_budget,
            remaining_budget=self.remaining_budget,
            total_bid_episode_num=total_bid_episode_num,
            remaining_bid_episode_num=remaining_bid_episode_num)

        return environment_status

    async def get_data_analysis(self, history, bidding_reference, environment_status):
        data_analyzer: DataAnalyzer = self.data_analyzer
        data_analysis_text, data_analysis_json = await data_analyzer.get_data_analysis(role_prompt=self.role_prompt,
                                                                                       history=history,
                                                                                       bidding_reference=bidding_reference,
                                                                                       environment_status=environment_status)
        return data_analysis_text, data_analysis_json

    def get_bidding_reference(self):

        bidding_reference = self.bidder.get_bidding_reference()
        bidding_factor = self.bidder.get_bidding_factor()
        return bidding_reference, bidding_factor

    async def get_bidding_strategy(self, **kwargs):
        formatted_time_str = kwargs['formatted_time_str']
        total_bid_episode_num = kwargs['total_bid_episode_num']
        remaining_bid_episode_num = kwargs['remaining_bid_episode_num']
        environment_status = self.get_environment_status(
            total_bid_episode_num=total_bid_episode_num,
            remaining_bid_episode_num=remaining_bid_episode_num)
        bidding_reference, bidding_factor = self.get_bidding_reference()
        history = await self.get_history_summary(action="output_bidding_strategy",formatted_time_str=formatted_time_str)
        data_analysis_text, data_analysis_json = await self.get_data_analysis(
            history=history,
            bidding_reference=bidding_reference,
            environment_status=environment_status
        )
        data_analysis_record_save_dir = os.path.join(self.workspace_root, "data_analysis", formatted_time_str)
        os.makedirs(data_analysis_record_save_dir, exist_ok=True)
        data_analysis_record_save_path = os.path.join(data_analysis_record_save_dir,
                                                      "{}.json".format(self.advertiser_id))
        with open(data_analysis_record_save_path, mode="w",
                  encoding='utf-8') as f:
            f.write(json.dumps(data_analysis_json, ensure_ascii=False, indent=4))
        self.set_todo(OutputBiddingStrategy())
        bidding_strategy = await self.todo.run(
            role_prompt=self.role_prompt,
            history=history,
            bidding_reference=bidding_reference,
            environment_status=environment_status,
            data_analysis=data_analysis_text
        )
        adjustment = bidding_strategy['adjustment']
        bidding_strategy['final_bidding_factor'] = bidding_factor * (1 + adjustment)
        bidding_strategy['bidding_factor'] = bidding_factor 
        self.completion_tokens = self.data_analyzer.llm.cost_manager.total_completion_tokens + \
                                 self.todo.llm.cost_manager.total_completion_tokens - self.completion_tokens
        self.prompt_tokens = self.data_analyzer.llm.cost_manager.total_prompt_tokens + \
                                 self.todo.llm.cost_manager.total_prompt_tokens - self.prompt_tokens

        return bidding_strategy
    
    async def get_bidding_strategy_with_experience(self, **kwargs):
        formatted_time_str = kwargs['formatted_time_str']
        total_bid_episode_num = kwargs['total_bid_episode_num']
        remaining_bid_episode_num = kwargs['remaining_bid_episode_num']
        environment_status = self.get_environment_status(
            total_bid_episode_num=total_bid_episode_num,
            remaining_bid_episode_num=remaining_bid_episode_num)
        bidding_reference, bidding_factor = self.get_bidding_reference()
        history = await self.get_history_summary(action="output_bidding_strategy",formatted_time_str=formatted_time_str)
        """
        train_experiences_json_path refers to a JSON file containing simulated bidding experiences, generated based on training data. 
        The data format follows the structure defined in the gen_initial_info() function.
        """
        experiences_prompt = await generate_experience_prompt("train_experiences_json_path",self.advertiser_id, self.budget_ratio, api_name=os.environ['MY_API_PARAM'] )
        data_analysis_text, data_analysis_json = await self.get_data_analysis(
            history=history+"\n"+experiences_prompt,
            bidding_reference=bidding_reference,
            environment_status=environment_status
        )
        data_analysis_record_save_dir = os.path.join(self.workspace_root, "data_analysis", formatted_time_str)
        os.makedirs(data_analysis_record_save_dir, exist_ok=True)
        data_analysis_record_save_path = os.path.join(data_analysis_record_save_dir,
                                                      "{}.json".format(self.advertiser_id))
        with open(data_analysis_record_save_path, mode="w",
                  encoding='utf-8') as f:
            f.write(json.dumps(data_analysis_json, ensure_ascii=False, indent=4))

        self.set_todo(OutputBiddingStrategy())
        bidding_strategy = await self.todo.run(
            role_prompt=self.role_prompt,
            history=history,
            bidding_reference=bidding_reference,
            environment_status=environment_status,
            data_analysis=data_analysis_text
        )
        adjustment = bidding_strategy['adjustment']
        bidding_strategy['final_bidding_factor'] = bidding_factor * (1 + adjustment)
        bidding_strategy['bidding_factor'] = bidding_factor 
        self.completion_tokens = self.data_analyzer.llm.cost_manager.total_completion_tokens + \
                                 self.todo.llm.cost_manager.total_completion_tokens - self.completion_tokens
        self.prompt_tokens = self.data_analyzer.llm.cost_manager.total_prompt_tokens + \
                                 self.todo.llm.cost_manager.total_prompt_tokens - self.prompt_tokens

        return bidding_strategy

    async def reflect(self, **kwargs):
        formatted_time_str = kwargs['formatted_time_str']
        history = await self.get_history_summary(action='reflect', formatted_time_str=formatted_time_str)

        self.set_todo(Reflect())
        reflect_result = await self.todo.run(
            role_prompt=self.role_prompt,
            history=history,
        )
        reflect_result_record_save_dir = os.path.join(self.workspace_root, "reflect", formatted_time_str)
        os.makedirs(reflect_result_record_save_dir, exist_ok=True)
        data_reflect_record_save_path = os.path.join(reflect_result_record_save_dir,
                                                     "{}.json".format(self.advertiser_id))
        with open(data_reflect_record_save_path, mode="w",
                  encoding='utf-8') as f:
            f.write(json.dumps(reflect_result, ensure_ascii=False, indent=4))

        return reflect_result

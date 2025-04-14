# *_*coding:utf-8 *_*
import asyncio
import json
import re
import os
from metagpt.actions import Action
from datetime import datetime
from metagpt.logs import logger

BASIC_DATA_TEMPLATE: str = """
### Basic Traffic Information (Data Source: Directly Obtained from the Environment)
- **Total Traffic Volume** (Total Number of Exposure Opportunities) :{traffic_num_sum}
- **Won Traffic Volume** (Volume of Successfully Bidded Exposures) :{num_won_sum}
- **Total Cost** (Daily Budget Consumption) :{market_cost_sum}
- **Total Budget**  (Daily Budget) :{given_budget}
- **Clicks** (Number of Successful Ad Clicks) :{click_sum}
- **CTR** (Click-Through Rate = Clicks / Won Traffic Volume) :{day_ctr}
- **Click Hourly** :{actual_click_list}
- **CTR Hourly** :{actual_click_rate_list}
- **Predict_CTR_Hourly** :{predict_click_rate_list}
- **Budget_use_rate_Hourly** (Hourly Spend Ratio) :{budget_use_rate_list}
- **Budget Utilization Rate** (Spent Budget / Allocated Budget) {budget_rate}
- **Cost per Click (CPC)** = Total Cost / Clicks, which helps to assess cost-effectiveness. {day_cpc}
"""

AGENT_DATA_TEMPLATE: str = """
### Bidding Strategy and Agent Behavior Information (Data Source: Agent Decisions)
- **Hourly Adjustment Parameters** (Adjustment Ratio per Hour) :{adjustment_list}
- **Reason for Adjustment** (Based on LLM Decision) :{reason_list}
"""

BASELINE_SIMULATION: str = """
### Performance and Budget Control under Baseline Algorithm
- **Total Cost** (Daily Budget Consumption) :{market_cost_sum_baseline}
- **Total Budget**  (Daily Budget) :{given_budget_baseline}
- **Clicks** (Number of Successful Ad Clicks) :{click_sum_baseline}
- **Click Hourly** : {actual_click_list_baseline}
- **Budget_use_rate_Hourly** (Hourly Spend Ratio) :{budget_use_rate_list_baseline}
"""

def gen_initial_info(info_dict, bsl_record):
    traffic_num_sum = 0
    num_won_sum = 0
    market_cost_sum = 0.0 
    click_sum = 0
    hour_list = list(info_dict.keys())
    given_budget = info_dict[hour_list[0]]['given_budget']
    bidding_factor = info_dict[hour_list[0]]['bid_factor']
    actual_click_list = []
    actual_click_rate_list = []
    predict_click_rate_list = []
    budget_use_rate_list = []
    adjustment_list = []
    reason_list = []
    for tmp_hour in hour_list:
        traffic_num_sum += info_dict[tmp_hour]['traffic_num']
        num_won_sum += info_dict[tmp_hour]['num_won']
        market_cost_sum += info_dict[tmp_hour]['market_cost']
        click_sum += info_dict[tmp_hour]['click']
        actual_click_list.append(info_dict[tmp_hour]['click'])
        actual_click_rate_list.append(info_dict[tmp_hour]['actual_click_rate'])
        predict_click_rate_list.append(info_dict[tmp_hour]['predict_click_rate'])
        adjustment_list.append(info_dict[tmp_hour]['adjustment'])
        reason_list.append(info_dict[tmp_hour]['reason'])
        budget_use_rate_list.append(info_dict[tmp_hour]['market_cost']/given_budget if given_budget > 0 else 0)
    day_ctr = click_sum / num_won_sum if num_won_sum > 0 else 0
    budget_rate = market_cost_sum / given_budget if given_budget > 0 else 0
    day_cpc = market_cost_sum / click_sum if click_sum > 0 else 0

    traffic_info = {
        "traffic_num_sum" : traffic_num_sum,
        "num_won_sum" : num_won_sum,
        "market_cost_sum" : market_cost_sum,
        "given_budget" : given_budget,
        "click_sum" : click_sum,
        "day_ctr" : day_ctr,
        "actual_click_list" : actual_click_list,
        "actual_click_rate_list" : actual_click_rate_list,
        "predict_click_rate_list" : predict_click_rate_list,
        "budget_use_rate_list" : budget_use_rate_list,
        "budget_rate" : budget_rate,
        "day_cpc" : day_cpc
    }

    bidding_behavior = {
        "bidding_factor": bidding_factor,
        "adjustment_list" : adjustment_list,
        "reason_list" : reason_list
    }
    if len(bsl_record) == 0:
        return {"traffic_info": traffic_info, "bidding_behavior": bidding_behavior}

    hour_list_baseline = list(bsl_record.keys())
    given_budget_baseline = bsl_record[hour_list_baseline[0]]['given_budget']
    bidding_factor_baseline = bsl_record[hour_list_baseline[0]]['bid_factor']
    market_cost_sum_baseline = 0.0 
    click_sum_baseline = 0
    actual_click_list_baseline = []
    budget_use_rate_list_baseline = []
    for tmp_hour in hour_list_baseline:
        market_cost_sum_baseline += bsl_record[tmp_hour]['market_cost']
        click_sum_baseline += bsl_record[tmp_hour]['click']
        actual_click_list_baseline.append(bsl_record[tmp_hour]['click'])
        budget_use_rate_list_baseline.append(bsl_record[tmp_hour]['market_cost']/given_budget if given_budget > 0 else 0)
    baseline_simulation = {
        "given_budget_baseline": given_budget_baseline,
        "market_cost_sum_baseline": market_cost_sum_baseline,
        "bidding_factor_baseline": bidding_factor_baseline,
        "click_sum_baseline": click_sum_baseline,
        "actual_click_list_baseline": actual_click_list_baseline,
        "budget_use_rate_list_baseline": budget_use_rate_list_baseline
    }
    

    return {"traffic_info": traffic_info, "bidding_behavior": bidding_behavior, "baseline_simulation": baseline_simulation}


class DailySummary(Action):
    PROMPT_TEMPLATE: str = """
    # YOUR ROLE
    You are a professional data analytics assistant responsible for generating a comprehensive **daily bidding performance report** for a client. The report should be data-driven, well-structured, and insightful.

    # BASIC TRAFFIC INSIGHTS
    The following are today's basic traffic metrics provided by the system:
    {traffic_info}

    # BIDDING STRATEGY & AGENT BEHAVIOR
    Below is the bidding strategy and agent's behavior log for today:
    {bidding_behavior}

    # REPORT REQUIREMENTS
    Please generate a comprehensive daily report with the following sections:
    1. **Key Market Insights**: 
    - Analyze CTR, CPC, competition intensity, and market trends.
    - Review budget consumption pattern (evenly distributed vs concentrated in specific hours).
    - Evaluate if ads were delivered to the right audience and analyze audience characteristics.
    - Analyze incremental value brought by agent optimization (additional clicks, saved budget, improved ROI).

    2. **Strategy Optimization Recommendations**:
    - Should the bidding strategy be adjusted? Why?
    - Should the budget allocation be adjusted? Why?
    - Review today's key bidding strategy adjustments and their outcomes (positive/negative).
    - Propose specific optimization suggestions for tomorrow and explain expected outcomes.

    3. **Overall Performance Summary**:
    - Summarize today's performance (CTR, CPC, ROI).
    - Highlight high-value placements or audiences.
    - Compare agent performance with estimated performance without agent involvement.
    - Present a case study focusing on one key event during the day (budget exhaustion, CTR spike, etc.), describing the agent's reaction and result, with lessons learned.

    Please return a JSON object strictly in the following format:
    ```json
    {{
        "Key Market Insights": "xxx",
        "Strategy Optimization Recommendations": "xxx",
        "Overall Performance Summary": "xxx"
    }}
    """

    max_try_num: int = 4
    log_directory: str = "/experiment_data/train/report_fail_mess"

    def gen_daily_summary(self, info_dict: dict):
        traffic_info, bidding_behavior = gen_initial_info(info_dict)
        

    async def generate_daily_report(self,
                                    info_dict: dict):

        traffic_info, bidding_behavior = gen_initial_info(info_dict)
        prompt = self.PROMPT_TEMPLATE.format(
            traffic_info=traffic_info,
            bidding_behavior=bidding_behavior
        )
        print(prompt)

        report_json_str = None
        try_num = 0
        current_time_str = datetime.now().strftime("%Y-%m-%d_%H")
        log_file_name = f"api_responses_{current_time_str}.txt"

        log_file_path = os.path.join(self.log_directory, log_file_name)
        if not os.path.exists(self.log_directory):
            os.makedirs(self.log_directory)
        while try_num < self.max_try_num:
            try_num += 1
            try:
                rsp = await self._aask(prompt)
                if try_num > self.max_try_num // 2:
                    self._log_api_response(rsp, log_file_path)

                report_json_str = self.parse_output(rsp)

                if self.check_data_integrity_and_types(report_json_str):
                    break
            except Exception as e:
                logger.exception(f"Failed to generate daily report (attempt {try_num})")

        if not report_json_str:
            raise ValueError("Failed to generate a valid report after maximum retries.")

        report_data: dict = json.loads(report_json_str)

        report_text = "\n".join(
            f"### {key}\n{value}\n" for key, value in report_data.items()
        )

        return traffic_info+bidding_behavior+report_text
    
    def _log_api_response(self, rsp: str, log_file_path: str):
        try:
            if not os.path.exists(log_file_path):
                with open(log_file_path, 'w') as f:
                    f.write("API Responses Log\n\n")

            with open(log_file_path, 'a') as f:
                f.write(f"API Response:\n{rsp}\n\n")
        except Exception as e:
            logger.exception("Failed to log API response.")

    @staticmethod
    def parse_output(rsp: str) -> str:
        pattern = r"```json(.*?)```"
        match = re.search(pattern, rsp, re.DOTALL)
        
        if match:
            code_text = match.group(1)
            
            cleaned_json_string = re.sub(r",\s*(?=[}\]])", "", code_text)
            
            return cleaned_json_string
        
        return rsp

    @staticmethod
    def check_data_integrity_and_types(json_data: str) -> bool:
        try:
            data = json.loads(json_data)
        except json.JSONDecodeError:
            return False

        required_keys = [
            "Key Market Insights",
            "Strategy Optimization Recommendations",
            "Overall Performance Summary"
        ]

        for key in required_keys:
            if key not in data:
                print(f"Missing required key: {key}")
                return False
            if not isinstance(data[key], str):
                print(f"Value of {key} should be string")
                return False

        return True


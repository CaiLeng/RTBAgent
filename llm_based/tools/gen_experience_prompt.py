# *_*coding:utf-8 *_*
import asyncio
import json
import re
import os
import sys

sys.path.append("/path/RTBAgent")

from metagpt.actions import Action
from metagpt.logs import logger

class SummarizeAdjustmentReason(Action):
    PROMPT_TEMPLATE: str = """
You are a bidding strategy analyst.

Below is the list of hourly bid adjustment factors applied by the agent on a given day:
ADJUSTMENT_LIST = {adjustment_list}

Here are the detailed reasons provided for each adjustment:
REASON_LIST = {reason_list}

Please summarize the overall adjustment trend and the general purpose behind these adjustments in one or two sentences.

Return your answer in the following JSON format:
```json
{{
    "summary_reason": str
}}
"""

    name: str = "SummarizeAdjustmentReason"
    max_try_num: int = 300

    async def run(self, adjustment_list, reason_list):
        prompt = self.PROMPT_TEMPLATE.format(
            adjustment_list=adjustment_list,
            reason_list=json.dumps(reason_list, ensure_ascii=False, indent=3)
        )
        print(prompt)

        try_num = 0
        json_data_str = None
        while try_num < self.max_try_num:
            try_num += 1
            try:
                rsp = await self._aask(prompt)
                json_data_str = self.parse_output(rsp)

                if self.check_data(json_data_str):
                    break
            except Exception as e:
                logger.exception(e)

        if json_data_str is None:
            return {"summary_reason": "A default summary: bid adjustments mostly aimed to improve CTR and budget efficiency."}
        else:
            return json.loads(json_data_str)

    @staticmethod
    def parse_output(rsp):
        pattern = r"```json(.*?)```"
        match = re.search(pattern, rsp, re.DOTALL)
        code_text = match.group(1) if match else rsp
        cleaned_json_string = re.sub(r",\s*(?=[}\]])", "", code_text)
        cleaned_json_string = re.sub(r"\n", "", cleaned_json_string)
        corrected_output = "{" + re.sub(r"^[{]|[}]$", "", cleaned_json_string) + "}"
        return corrected_output

    @staticmethod
    def check_data(json_data_str):
        try:
            data = json.loads(json_data_str)
        except json.JSONDecodeError:
            return False

        if "summary_reason" not in data:
            return False

        if not isinstance(data["summary_reason"], str):
            return False

        return True


async def generate_experience_prompt(json_root, adv_id, budget_r, api_name="ollama_v1", renew=False, top_n=5):
    json_dir = os.path.join(json_root, "llm_fp", api_name, budget_r, adv_id)
    prompt_path = os.path.join(json_dir, "experience_prompt.txt")
    print(prompt_path)

    if os.path.exists(prompt_path) and not renew:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()

    date_list = list(os.listdir(json_dir))
    prompt = "### EXPERIENCE REFERENCE (High-Quality Bidding Behaviors from Training Phase)\n\n"
    prompt += "Below are several bidding behavior examples from training phase, selected from best-performing trials of the respective days the previous {} days.\n".format(len(date_list))
    experience_ind = 0

    for i_date_dir in date_list:
        experience_dir = os.path.join(json_dir, i_date_dir)
        if not os.path.isdir(experience_dir):
            continue

        score_path_list = []
        for fname in os.listdir(experience_dir):
            if not fname.endswith(".json"):
                continue
            file_path = os.path.join(experience_dir, fname)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    records = json.load(f)
                i_improvement = records['traffic_info']['click_sum'] - records['baseline_simulation']['click_sum_baseline']
                if i_improvement <= 0:
                    continue
                score_path_list.append((i_improvement, file_path))
            except Exception:
                continue

        score_path_list.sort(key=lambda x: x[0], reverse=True)
        top_n = min(top_n, len(score_path_list))
        top_experiences = score_path_list[:top_n]
        for _, best_path in top_experiences:
            experience_ind += 1
            single_day_prompt = await gen_experience_prompt_single_day(experience_ind, best_path)
            prompt += single_day_prompt

    prompt += "\nUse the above examples as reference to design your strategy under the current testing environment.\n"
    with open(prompt_path, 'w', encoding='utf-8') as f:
        f.write(prompt)
    return prompt

    

async def gen_experience_prompt_single_day(experience_ind, json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        record = json.load(f)

    traffic = record['traffic_info']
    behavior = record['bidding_behavior']
    baseline = record.get('baseline_simulation', {})

    clicks_str = f"increased from {baseline.get('click_sum_baseline', 'N/A')} to {traffic['click_sum']}" \
        if 'click_sum_baseline' in baseline else str(traffic['click_sum'])
    baseline_budget_used = baseline.get('market_cost_sum_baseline', None)
    given_budget = traffic['given_budget']
    if baseline_budget_used is not None and given_budget > 0:
        baseline_budget_str = f"{baseline_budget_used} / {given_budget}"
    else:
        baseline_budget_str = "N/A"

    prompt = f"\n--- Example {experience_ind} ---\n"
    prompt += f"Traffic Summary:\n"
    prompt += f"- Total Traffic: {traffic['traffic_num_sum']}\n"
    prompt += f"- Impressions Won: {traffic['num_won_sum']}\n"
    prompt += f"- Budget Used: {traffic['market_cost_sum']} / {traffic['given_budget']}"
    prompt += f"- Baseline Budget Used: {baseline_budget_str}\n"
    prompt += f"- Total Clicks: {clicks_str}\n"
    prompt += f"- Day CTR: {traffic['day_ctr']:.6f}\n"
    prompt += f"- Day CPC: {traffic['day_cpc']:.2f}\n"

    prompt += f"\nBidding Strategy Summary:\n"
    prompt += f"- Baseline Bidding Factor: {behavior['bidding_factor']}\n"
    prompt += f"- Adjustment Pattern (hourly): {behavior['adjustment_list']}\n"
    prompt += f"- Click (hourly): {traffic['actual_click_list']}\n"

    action = SummarizeAdjustmentReason()
    res = await action.run(behavior['adjustment_list'], behavior['reason_list'])

    prompt += f"- Reasoning Summary: {res}\n"

    return prompt




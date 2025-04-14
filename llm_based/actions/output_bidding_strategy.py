# *_*coding:utf-8 *_*
import asyncio
import json
import re

from metagpt.actions import Action
from metagpt.logs import logger

class OutputBiddingStrategy(Action):
    PROMPT_TEMPLATE: str  = """
# YOUR ROLE
{role_prompt}

# CONTEXT
{history}

# THE REFERENCE BIDDING FACTOR GIVEN BY THE BIDDING ALGORITHM FOR ADVERTISER
{bidding_reference}

# ENVIRONMENT STATUS
{environment_status}

# DATA ANALYSIS
{data_analysis}

# NOW YOUR ACTION IS
The bidding factor for this period = the bidding factor given by the algorithm * (1+adjustment)
The selection space for "adjustment" is a continuous range within [-0.5, 0.5].

When selecting the "adjustment" prioritize a balance between budget efficiency and click volume by exploring values across the entire range. 
Rather than defaulting to common values like 0.1 or -0.1, consider more precise adjustments that include multiple decimal places to better adapt to historical performance and current market conditions, maximizing potential outcomes through fine-tuned selections.

Please output the "adjustment" you have selected and explain the reason with a maximum word count of 80 words, and return it in the following JSON format:
```json
{{
    "adjustment": float = xx,
    "reason": str = xx
}}

"""


    name: str = "OutputBiddingStrategy"
    max_try_num:int = 1000

    async def run(self,
                  role_prompt,
                  history,
                  bidding_reference,
                  environment_status,
                  data_analysis
                  ):

        prompt = self.PROMPT_TEMPLATE.format(
            role_prompt = role_prompt,
            history = history,
            bidding_reference = bidding_reference,
            environment_status = environment_status,
            data_analysis =  data_analysis
            )
        print(prompt)

        json_data_str = None
        try_num = 0
        while try_num < self.max_try_num:
            try_num+=1
            try:

                rsp = await self._aask(prompt)

                json_data_str= OutputBiddingStrategy.parse_output(rsp)

                check_data_correct = self.check_data_integrity_and_types(json_data_str)

                if check_data_correct:
                    break
                else:
                    continue
            except Exception as e:
                logger.exception(f"{e}")

        if json_data_str is None:
            return {
                "adjustment": 0.0000,
                "reason": "default value"
            }
        else:
            tmp_out = json.loads(json_data_str)
            tmp_out["adjustment"] = round(tmp_out["adjustment"], 4)
            return tmp_out

    @staticmethod
    def parse_output(rsp):
        pattern = r"```json(.*)```"
        match = re.search(pattern, rsp, re.DOTALL)
        code_text = match.group(1) if match else rsp
        cleaned_json_string = re.sub(r",\s*(?=[}\]])", "", code_text)           # 排除最后一个键值对后有非法','号
        cleaned_json_string = re.sub(r'\n', '', cleaned_json_string)            # 暴力排除非法“\n”
        corrected_output = "{" + re.sub(r'[{}]', '', cleaned_json_string) + "}"
        return corrected_output

    @staticmethod
    def check_data_integrity_and_types(json_data_str):

        try:
            data = json.loads(json_data_str)
        except json.JSONDecodeError:
            return False

        required_keys = ["adjustment", "reason"]
        for key in required_keys:
            if key not in data:
                return False

        if not isinstance(data["adjustment"], float):
            return False

        if data["adjustment"]<-0.5 or data["adjustment"]>0.5:
            return False

        if not isinstance(data["reason"], str):
            return False

        return True



if __name__ == '__main__':

    async def test():
        action = OutputBiddingStrategy()

        res = await action.run(project_background_prompt = "",
            role_prompt = "",
            bidding_reference = "",
            environment_status = "",
            data_analysis =  "")
        print(res)

    asyncio.run(test())

# *_*coding:utf-8 *_*
import asyncio
import json
import re

from metagpt.actions import Action
from metagpt.logs import logger


class DataAnalyzer(Action):
    PROMPT_TEMPLATE: str = """
# YOUR ROLE
{role_prompt}

# CONTEXT
{history}

# THE REFERENCE GIVEN BY THE BIDDING ALGORITHM FOR ADVERTISER
{bidding_reference}

# ENVIRONMENT STATUS
{environment_status}

# NOW YOUR ACTION IS
The bidding factor for this period = the bidding factor given by the algorithm * (1+adjustment)
Now, you need to analyze the advantages and disadvantages of each "adjustment range" based on historical decisions, current environmental conditions, and algorithm suggestions. 
The selection space for "adjustment range" is from {{[-0.5,-0.4), [-0.4,-0.3), [-0.3,-0.2), [-0.2,-0.1), [-0.1,0.0), [0.0,0.1), [0.1,0.2), [0.2,0.3), [0.3,0.4), [0.4,0.5]}}.

While making your analysis, consider the following:
1. **Historical Performance**: Adjustments that have previously optimized budget usage and improved click volume without significantly impacting the win rate are valuable.
2. **Exploration of New Adjustments**: Exploring new adjustment ranges, especially positive adjustments range like [0.0,0.1), [0.1,0.2), and [0.2,0.3), can potentially uncover more effective strategies. Increasing the bid may improve visibility and click volume, particularly in competitive environments.
3. **Balancing Stability and Innovation**: Strive to balance between maintaining strategies that have shown consistent performance and exploring new adjustments. A mix of historical strategy and new exploration, with a focus on positive adjustments, could provide a balanced approach to ensure cost efficiency, maximize clicks, and adapt to market changes.

Please output a JSON in the following format for all analyses, with a maximum word count of 500 words:
```json
{{
    "adjustment range for [-0.5,-0.4)": str = xx,
    "adjustment range for [-0.4,-0.3)": str = xx,
    "adjustment range for [-0.3,-0.2)": str = xx,
    "adjustment range for [-0.2,-0.1)": str = xx,
    "adjustment range for [-0.1,0.0)": str = xx,
    "adjustment range for [0.0,0.1)": str = xx,
    "adjustment range for [0.1,0.2)": str = xx,
    "adjustment range for [0.2,0.3)": str = xx,
    "adjustment range for [0.3,0.4)": str = xx,
    "adjustment range for [0.4,0.5]": str = xx
}}
"""
    name: str = "DataAnalyzer"
    max_try_num: int = 1000

    async def get_data_analysis(self,
                  role_prompt,
                  history,
                  bidding_reference,
                  environment_status):
        prompt = self.PROMPT_TEMPLATE.format(
            role_prompt=role_prompt,
            history=history,
            bidding_reference=bidding_reference,
            environment_status=environment_status)
        json_data_str = None
        try_num = 0
        while try_num < self.max_try_num:
            try_num += 1
            try:

                rsp = await self._aask(prompt)

                json_data_str = DataAnalyzer.parse_output(rsp)

                check_data_correct = self.check_data_integrity_and_types(json_data_str)

                if check_data_correct:
                    break
                else:
                    continue
            except Exception as e:
                logger.exception(e)
        analysis_result_json: dict = json.loads(json_data_str)
        data_analysis_text = "\n".join(
            f"- {key}: {content}" for key, content in analysis_result_json.items()
        )
        return data_analysis_text, analysis_result_json

    @staticmethod
    def parse_output(rsp):
        pattern = r"```json(.*)```"
        match = re.search(pattern, rsp, re.DOTALL)
        code_text = match.group(1) if match else rsp
        cleaned_json_string = re.sub(r",\s*(?=[}\]])", "", code_text)
        cleaned_json_string = re.sub(r'\n', '', cleaned_json_string)
        corrected_output = "{" + re.sub(r'[{}]', '', cleaned_json_string) + "}"
        return corrected_output

    @staticmethod
    def check_data_integrity_and_types(json_data):

        try:
            data = json.loads(json_data)
        except json.JSONDecodeError:
            return False

        required_keys = [
            "adjustment range for [-0.5,-0.4)",
            "adjustment range for [-0.4,-0.3)",
            "adjustment range for [-0.3,-0.2)",
            "adjustment range for [-0.2,-0.1)",
            "adjustment range for [-0.1,0.0)" ,
            "adjustment range for [0.0,0.1)" ,
            "adjustment range for [0.1,0.2)",
            "adjustment range for [0.2,0.3)",
            "adjustment range for [0.3,0.4)",
            "adjustment range for [0.4,0.5]",
                ]
        for key in required_keys:
            if key not in data:
                return False

            if not isinstance(data[key], str):
                return False

        return True

if __name__ == '__main__':

    async def test():
        action = DataAnalyzer()

        res = await action.get_data_analysis(project_background_prompt = "",
                  role_prompt = "",
                  history = "",
                  bidding_reference= "",
                  environment_status= "")
        print(res)

    asyncio.run(test())

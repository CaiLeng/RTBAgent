# *_*coding:utf-8 *_*
import asyncio
import json
import re

from metagpt.actions import Action
from metagpt.logs import logger


class Reflect(Action):
    PROMPT_TEMPLATE: str = """

# YOUR ROLE
{role_prompt}

# CONTEXT
{history}

# NOW YOUR ACTION IS
Please reflect deeply on your bidding decision based on today's operations and market feedback. Consider the following aspects:
-The outcome of bidding decision: Did your bid achieve the expected effect? If not, what factors are causing it?
-Accuracy of data analysis: Is your data analysis accurate? Are there any missing or misunderstood data?
-The necessity of strategy adjustment: Based on the current market situation and your bidding results, is it necessary to adjust the strategy?
-Improvement measures: How do you plan to improve your future bidding strategy to increase effectiveness?



Please return it in the following JSON format with NO other texts :

```json
{{
    "evaluation_of_bid_results": str = xx,
    "data_analysis_accuracy": str = xx,
    "policy_adjustment_suggestions": str = xx,
    "improvement_measures": str = xx,
}}
```

"""

    name: str = "Reflect"
    max_try_num: int = 300

    async def run(self,
                  role_prompt,
                  history
                  ):
        prompt = self.PROMPT_TEMPLATE.format(
            role_prompt=role_prompt,
            history=history
        )
        print(prompt)
        try_num = 0
        while try_num < self.max_try_num:
            try_num += 1
            try:

                rsp = await self._aask(prompt)

                json_data_str = Reflect.parse_output(rsp)

                check_data_correct = self.check_data_integrity_and_types(json_data_str)

                if check_data_correct:
                    break
                else:
                    continue
            except Exception as e:
                logger.exception(e)

        return json.loads(json_data_str)

    @staticmethod
    def parse_output(rsp):
        try:
            pattern = r"```json(.*)```"
            match = re.search(pattern, rsp, re.DOTALL)
            code_text = match.group(1) if match else rsp
            data = json.loads(code_text)
        except Exception as e:
            pattern = r"```(.*?)```"
            match = re.search(pattern, rsp, re.DOTALL)
            code_text = match.group(1) if match else rsp
            data = json.loads(code_text)
        return code_text

    @staticmethod
    def check_data_integrity_and_types(json_data):

        try:
            data = json.loads(json_data)
        except json.JSONDecodeError:
            return False

        required_keys = ["evaluation_of_bid_results",
                         "data_analysis_accuracy",
                         "policy_adjustment_suggestions",
                         "improvement_measures"]
        for key in required_keys:
            if key not in data:
                return False

            if not isinstance(data[key], str):
                return False

        return True


if __name__ == '__main__':
    async def test():
        action = Reflect()

        res = await action.run(project_background_prompt='1',
                               role_prompt='2',
                               history='3',
                               )
        print(res)


    asyncio.run(test())

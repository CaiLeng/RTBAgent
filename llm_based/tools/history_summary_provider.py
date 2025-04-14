# *_*coding:utf-8 *_*
import json
import re
import os
from datetime import datetime

import pandas as pd

from metagpt.actions import Action
from metagpt.logs import logger


class HistorySummaryProvider(Action):
    advertiser_id: str

    workspace_root: str


    @staticmethod
    def parse_output(rsp):
        try:
            pattern = r"```json(.*)```"
            match = re.search(pattern, rsp, re.DOTALL)
            code_text = match.group(1) if match else rsp
            cleaned_json_string = re.sub(r",\s*(?=[}\]])", "", code_text)
            cleaned_json_string = re.sub(r'\n', '', cleaned_json_string)
            corrected_output = "{" + re.sub(r'[{}]', '', cleaned_json_string) + "}"
        except Exception as e:
            pattern = r"```(.*?)```"
            match = re.search(pattern, rsp, re.DOTALL)
            code_text = match.group(1) if match else rsp
            cleaned_json_string = re.sub(r",\s*(?=[}\]])", "", code_text)
            cleaned_json_string = re.sub(r'\n', '', cleaned_json_string)
            corrected_output = "{" + re.sub(r'[{}]', '', cleaned_json_string) + "}"
        return corrected_output

    @staticmethod
    def check_data_integrity_and_types(json_data, required_keys):
        try:
            data = json.loads(json_data)
        except json.JSONDecodeError:
            return False

        for key in required_keys:
            if key not in data:
                print(f"缺少必要的键: {key}")
                return False

            if not isinstance(data[key], str):
                return False

        return True

    async def ask_llm_history_summary(self, llm_prompt):
        json_data_str = None
        max_try_num = 200
        try_num = 0
        while try_num < max_try_num:
            try_num += 1
            try:
                print(llm_prompt)
                response = await self._aask(llm_prompt)
                json_data_str = HistorySummaryProvider.parse_output(response)
                check_data_correct = self.check_data_integrity_and_types(json_data=json_data_str,
                                                                         required_keys=['summary'])
                if check_data_correct:
                    break
                else:
                    continue
            except Exception as e:
                logger.exception(e)

        if json_data_str:
            try:
                return json.loads(json_data_str).get('summary')
            except json.JSONDecodeError as e:
                logger.exception(e)
                json_data_dict = {
                    "summary": "fail to summary"
                }
                return json_data_dict["summary"]
        else:
            json_data_dict = {
                "summary": "fail to summary"
            }
            logger.exception("Failed to get a valid response after max attempts")
            return json_data_dict["summary"]

    async def get_history_bidding_summary(self,formatted_time_str):

        env_record_save_dir = os.path.join(self.workspace_root, "env_summary")

        if os.path.exists(env_record_save_dir) is False:
            return ""

        time_names = os.listdir(env_record_save_dir)
        dates = [datetime.strptime(date, '%Y-%m-%d-%H') for date in time_names]
        dates.sort()
        time_names = [datetime.strftime(date, '%Y-%m-%d-%H') for date in dates]

        time_names  = reversed(time_names)

        records = []

        has_add_adv_ids = []

        for time_name in time_names:
            time_dir = os.path.join(env_record_save_dir, time_name)
            if not os.path.exists(time_dir):
                continue
            adv_ids = os.listdir(time_dir)
            for adv_id in adv_ids:
                if adv_id.split(".")[0] == self.advertiser_id:
                    if adv_id.split('.')[0] in has_add_adv_ids:
                        continue

                    json_path = os.path.join(time_dir, adv_id)
                    record = json.loads(pd.read_json(json_path, typ='series').to_json())
                    record_text = ""

                    for key in record.keys():
                        text = "- {key}:{content}\n".format(key=key, content=record[key])
                        record_text += text
                    records.append(f"time: {time_name}\n"
                                   f"advertiser_id: {adv_id.split('.')[0]}\n"
                                   f"env_info:\n{record_text} ")
                    has_add_adv_ids.append(adv_id.split('.')[0])

        texts = []

        for m in records:
            texts.append(m)
        text = "\n".join(texts)

        return text

    def parse_folder_name(self, folder_name):
        try:
            return datetime.strptime(folder_name, "%Y-%m-%d-%H")
        except ValueError:
            return None

    def get_latest_day_folders(self, folders):
        parsed_folders = [(folder, self.parse_folder_name(folder)) for folder in folders]

        valid_folders = [folder for folder in parsed_folders if folder[1] is not None]

        if not valid_folders:
            return []

        latest_day = max(folder[1].date() for folder in valid_folders)

        latest_day_folders = [folder[0] for folder in valid_folders if folder[1].date() == latest_day]

        return sorted(latest_day_folders)

    async def get_today_bidding_summary(self, formatted_time_str):
        env_record_save_dir = os.path.join(self.workspace_root, "env")

        if os.path.exists(env_record_save_dir) is False:
            return ""

        time_names = os.listdir(env_record_save_dir)
        time_names = self.get_latest_day_folders(time_names)
        adjustment_hist = ""
        records = []
        for time_name in time_names:
            time_dir = os.path.join(env_record_save_dir, time_name)
            if not os.path.exists(time_dir):
                continue
            adv_ids = os.listdir(time_dir)
            for adv_id in adv_ids:
                if adv_id.split(".")[0] == self.advertiser_id:
                    json_path = os.path.join(time_dir, adv_id)
                    record = json.loads(pd.read_json(json_path, typ='series').to_json())
                    record_text = ""
                    for key in record.keys():
                        text = "- {key}:{content}\n".format(key=key, content=record[key])
                        record_text += text
                    records.append(f"time: {time_name}\n"
                                   f"advertiser_id: {adv_id.split('.')[0]}\n"
                                   f"env_info:\n{record_text} ")
                    with open(json_path, 'r', encoding='utf-8') as temp_f:
                        data = json.load(temp_f)
                        if 'adjustment' in data:
                            adjustment_hist += f"{time_name} adjustment: {data['adjustment']}\n"

        texts = []
        for m in records:
            texts.append(m)
        text = "\n".join(texts)
        text_length = len(text)
        max_words = 2000
        if text_length < 50:
            return text
        else:
            prompts = """
You are an RTB (Real-Time Bidding) summary tool with expertise in analyzing and summarizing bid data. Your task is to create a concise summary that highlights trends, adjustments, and outcomes from each bidding session, focusing on key performance metrics and decision-making effectiveness.

For the provided bid session data, summarize the following aspects:
- **Bid Adjustment**: Analyze the bidding adjustment factor and its reasoning. Indicate if the adjustment was positive, negative, or neutral, and summarize the rationale.
- **Performance Metrics**: Summarize click outcomes, predicted vs. actual click rates, average bid price, average market price, and win rate.
- **Budget Usage**: Comment on budget utilization, including the given budget, remaining budget, and the number of remaining bid episodes.
- **Traffic Analysis**: Provide insights on traffic volume and overall efficiency of bidding, highlighting whether the bids were effective based on the actual click outcomes and predicted click rates.

Summarize with a maximum word count of 300 words and return the output strictly in the following JSON format, without any additional text or explanations:

```json
{{
    "summary": str = xx
}}
```
                    """
        llm_prompt = f"""
{text}

{prompts}
               """
        summary = await self.ask_llm_history_summary(llm_prompt=llm_prompt)
        summary_plus = f"[{adjustment_hist}]\n" \
                       f"{summary}"
        return summary_plus

    async def get_history_reflect_summary(self, formatted_time_str):
        reflect_record_save_dir = os.path.join(self.workspace_root, "reflect")

        if os.path.exists(reflect_record_save_dir) is False:
            return ""

        time_names = os.listdir(reflect_record_save_dir)
        records = []
        for time_name in time_names:
            time_dir = os.path.join(reflect_record_save_dir, time_name)
            if not os.path.exists(time_dir):
                continue
            adv_ids = os.listdir(time_dir)
            for adv_id in adv_ids:
                if adv_id.split(".")[0] == self.advertiser_id:
                    json_path = os.path.join(time_dir, adv_id)
                    record = json.loads(pd.read_json(json_path, typ='series').to_json())

                    record_text = ""
                    for key in record.keys():
                        text = "- {key}:{content}\n".format(key=key, content=record[key])
                        record_text += text
                    records.append(f"time: {time_name}\n"
                                   f"advertiser_id: {adv_id.split('.')[0]}\n"
                                   f"reflect_info:\n{record_text} ")

        texts = []
        for m in records:
            texts.append(m)
        text = "\n".join(texts)
        text_length = len(text)
        max_words = 2000
        if text_length < 50:
            return text
        else:
            prompts = """
You are a historical summary tool for reflective insight, skilled at summarizing the trends and core of reflective behavior

Summarize with a maximum word count of 100 words and return the output strictly in the following JSON format, without any additional text or explanations:

```json
{{
    "summary": str = xx
}}
```
                    """
        llm_prompt = f"""
{text}

{prompts}
                   """
        summary = await self.ask_llm_history_summary(llm_prompt=llm_prompt)
        return summary

    async def get_history_summary(self, action='',formatted_time_str=''):
        summary_dict = {}


        if action == 'output_bidding_strategy':
            history_bidding_summary = await self.get_history_bidding_summary(formatted_time_str)
            history_reflect_summary = await self.get_history_reflect_summary(formatted_time_str)
            today_bidding_summary = await self.get_today_bidding_summary(formatted_time_str)

            summary_dict = {
                "history_bidding_summary": history_bidding_summary,
                "history_reflect_summary": history_reflect_summary,
                "today_bidding_summary": today_bidding_summary
            }

        elif action == 'reflect':
            history_bidding_summary = await self.get_history_bidding_summary(formatted_time_str)
            history_reflect_summary = await self.get_history_reflect_summary(formatted_time_str)
            today_bidding_summary = await self.get_today_bidding_summary(formatted_time_str)

            summary_dict = {
                "history_bidding_summary": history_bidding_summary,
                "history_reflect_summary": history_reflect_summary,
                "today_bidding_summary": today_bidding_summary
            }

        summary_text = ""
        for key in summary_dict.keys():
            text = "- {key}:{content}\n".format(key=key, content=summary_dict[key])
            summary_text += text

        print(summary_text)


        return summary_text

import json
import copy
from enum import Enum

from typing import List, Dict
# 使用 buckyos-py-runtime中的ndn实现
# from .ndn import NDNItem, NDNDataBase

import logging
logger = logging.getLogger(__name__)


class LLMPrompt:
    def __init__(self,prompt_str = None) -> None:
        self.messages : List[Dict] = []
        if prompt_str:
            self.messages.append({"role":"user","content":prompt_str})
        self.system_message : Dict = None
        self.inner_functions : List[Dict] = []

    def append_system_message(self,content:str):
        if content is None:
            return

        if self.system_message is None:
            self.system_message = {"role":"system","content":content}
        else:
            self.system_message["content"] += content

    def append_user_message(self,content:str):
        if content is None:
            return

        self.messages.append({"role":"user","content":content})

    def as_str(self)->str:
        result_str = ""
        if self.system_message:
            result_str = json.dumps(self.system_message,ensure_ascii=False)
        if self.messages:
            result_str += json.dumps(self.messages,ensure_ascii=False)
        if self.inner_functions:
            result_str += json.dumps(self.inner_functions,ensure_ascii=False)

        return result_str

    def to_message_list(self)->List[Dict]:
        result = []
        if self.system_message:
            result.append(self.system_message)
        result.extend(self.messages)
        return result



    def append(self,prompt:'LLMPrompt'):
        if prompt is None:
            return

        if prompt.inner_functions:
            if self.inner_functions is None:
                self.inner_functions = copy.deepcopy(prompt.inner_functions)
            else:
                self.inner_functions.extend(prompt.inner_functions)

        if prompt.system_message is not None:
            if self.system_message is None:
                self.system_message = copy.deepcopy(prompt.system_message)
            else:
                self.system_message["content"] += prompt.system_message.get("content")

        self.messages.extend(prompt.messages)

    def load_from_config(self,config:List[Dict]) -> bool:
        if isinstance(config,list) is not True:
            logger.error("prompt is not list!")
            return False
        self.messages : List[Dict] = []
        for msg in config:
            if msg.get("content"):
                if msg.get("role") == "system":
                    self.system_message = msg
                else:
                    self.messages.append(msg)
            else:
                logger.error("prompt message has no content!")
        return True

class LLMInput:
    def __init__(self, prompt: LLMPrompt = None, NDN_ids: Dict[str, str] = None) -> None:
        self.prompt: LLMPrompt = prompt if prompt else LLMPrompt()
        self.NDN_ids: Dict[str, str] = NDN_ids if NDN_ids else {}
        self.NDN_items: Dict[str, NDNItem] = self._get_items(self.NDN_ids)  # key is the reference, value is NDNItem

    def _get_items(NDN_ids: Dict[str, str]) -> Dict[str, NDNItem]:
        items: Dict[str, NDNItem] = {}
        database = NDNDataBase.get_instance()
        if NDN_ids is None:
            return items

        for ref, name in NDN_ids.items():
            item = database.get_item(name)
            items[ref] = item

        return items



class LLMResultStates(Enum):
    IGNORE = "ignore"
    OK = "ok" # process done
    ERROR = "error"

class LLMResult:
    def __init__(self) -> None:
        self.state : str = LLMResultStates.IGNORE
        self.compute_error_str = None
        self.resp : str = "" # llm say:
        self.raw_result = None # raw result from compute kernel
        #self.inner_functions : List[AIFunction] = []
        self.action_list : List[ActionNode] = [] # op_list is a optimize design for saving token


    @classmethod
    def from_error_str(self,error_str:str) -> 'LLMResult':
        r = LLMResult()
        r.state = LLMResultStates.ERROR
        r.error_str = error_str
        return r

    @classmethod
    def from_json_str(self,llm_json_str:str) -> 'LLMResult':
        r = LLMResult()
        if llm_json_str is None:
            r.state = LLMResultStates.IGNORE
            return r
        if llm_json_str == "**IGNORE**":
            r.state = LLMResultStates.IGNORE
            return r

        r.state = LLMResultStates.OK

        llm_json = json.loads(llm_json_str)
        r.resp = llm_json.get("resp")
        r.raw_result = llm_json
        action_list = llm_json.get("actions")
        if action_list:
            for action in action_list:
                action_item = ActionNode.from_json(action)
                if action_item:
                    r.action_list.append(action_item)

        return r

    @classmethod
    def parse_action(cls,func_string:str):
        str_list = shlex.split(func_string)
        func_name = str_list[0]
        params = str_list[1:]
        return func_name, params

    @classmethod
    def from_str(self,llm_result_str:str,valid_func:List[str]=None) -> 'LLMResult':
        r = LLMResult()

        if llm_result_str is None:
            r.state = LLMResultStates.IGNORE
            return r
        if llm_result_str == "**IGNORE**":
            r.state = LLMResultStates.IGNORE
            return r

        try:
            if llm_result_str[0] == "{":
                return LLMResult.from_json_str(llm_result_str)

            if llm_result_str.lstrip().rstrip().startswith("```json"):
                return LLMResult.from_json_str(llm_result_str[7:-3])
        except:
            pass

        lines = llm_result_str.splitlines()
        is_need_wait = False

        def check_args(action_item:ActionNode):
            match action_item.name:
                case "post_msg":# /post_msg $target_id
                    if len(action_item.args) != 1:
                        return False

                    new_msg = AgentMsg()
                    target_id = action_item.args[0]
                    msg_content = action_item.body
                    new_msg.set("",target_id,msg_content)

                    return True


            return False


        current_action : ActionNode = None
        for line in lines:
            if line.startswith("##/"):
                if current_action:
                    if check_args(current_action) is False:
                        r.resp += current_action.dumps()
                    else:
                        r.action_list.append(current_action)

                action_name,action_args = LLMResult.parse_action(line[3:])
                current_action = ActionNode(action_name,action_args)
            else:
                if current_action:
                    current_action.append_body(line + "\n")
                else:
                    r.resp += line + "\n"

        if current_action:
            if check_args(current_action) is False:
                r.resp += current_action.dumps()
            else:
                r.action_list.append(current_action)

        r.state = LLMResultStates.OK
        return r

# Old name is behavior, I belive new name "llm_process" is better
# pylint:disable=E0402

from abc import ABC,abstractmethod

import copy
import json

from typing import Dict,List
from enum import Enum
from .llm_context import *
from ..llm_base import *

import logging
logger = logging.getLogger(__name__)

MIN_PREDICT_TOKEN_LEN = 32

class BaseLLMProcess(ABC):
    def __init__(self) -> None:
        self.behavior:str = None #行为名字
        self.goal:str = None #目标
        self.input_example:str= None #输入样例
        self.result_example:str = None #llm_result样例

        self.enable_json_resp = False
        #None means system default,
        self.model_name = None
        self.max_token = 2000 # result_token
        self.max_prompt_token = 2000 # not include input prompt
        self.chat_summary_token_len = 500
        self.timeout = 1800 # 30 min

        self.llm_context:LLMProcessContext = None


    @abstractmethod
    async def prepare_prompt(self,input:Dict) -> LLMPrompt:
        pass

    @abstractmethod
    async def get_inner_function_for_exec(self,func_name:str) -> AIFunction:
       pass

    @abstractmethod
    def prepare_inner_function_context_for_exec(self,inner_func_name:str,parameters:Dict):
        return

    @abstractmethod
    async def on_post_llm_process(self,actions:List[ActionNode],input:Dict,llm_result:LLMResult) -> bool:
        pass

    def get_remain_prompt_length(self,prompt:LLMPrompt,will_append_str:str) -> int:
        return self.max_prompt_token - ComputeCenter.llm_num_tokens(prompt,self.model_name)

    @abstractmethod
    async def load_from_config(self,config:dict) -> bool:
        #self.behavior = config.get("behavior")
        #self.goal = config.get("goal")
        self.input_example = config.get("input_example")
        self.result_example = config.get("result_example")

        if config.get("model_name"):
            self.model_name = config.get("model_name")
        if config.get("enable_json_resp"):
            self.enable_json_resp = config.get("enable_json_resp") == "true"
        if config.get("max_token"):
            self.max_token = config.get("max_token")
        if config.get("timeout"):
            self.timeout = config.get("timeout")


        return True

    @abstractmethod
    async def initial(self,params:Dict = None) -> bool:
        pass

    def _format_content_by_env_value(self,content:str,env:Dict)->str:
        return content.format_map(env)

    async def _execute_inner_func(self,inner_func_call_node:Dict,prompt: LLMPrompt,stack_limit = 1) -> ComputeTaskResult:
        arguments = None
        stack_limit = stack_limit - 1
        try:
            func_name = inner_func_call_node.get("name")
            arguments = json.loads(inner_func_call_node.get("arguments"))
            logger.info(f"LLMProcess execute inner func:{func_name} :({json.dumps(arguments,ensure_ascii=False)})")

            func_node : AIFunction = await self.get_inner_function_for_exec(func_name)
            if func_node is None:
                result_str:str = f"execute {func_name} error,function not found"
            else:
                self.prepare_inner_function_context_for_exec(func_name,arguments)
                result_str:str = await func_node.execute(arguments)
        except Exception as e:
            result_str = f"execute {func_name} error:{str(e)}"
            logger.error(f"LLMProcess execute inner func:{func_name} error:\n\t{e}")

        logger.info("LLMProcess execute inner func result:" + result_str)

        prompt.messages.append({"role":"function","content":result_str,"name":func_name})
        if self.enable_json_resp:
            resp_mode = "json"
        else:
            resp_mode = "text"

        max_result_token = self.max_token - ComputeCenter.llm_num_tokens(prompt,self.model_name)
        if max_result_token < MIN_PREDICT_TOKEN_LEN:
            task_result = ComputeTaskResult()
            task_result.result_code = ComputeTaskResultCode.ERROR
            task_result.error_str = f"prompt too long,can not predict"
            return task_result

        if stack_limit > 0:
            inner_functions=prompt.inner_functions
        else:
            inner_functions = None


        task_result: ComputeTaskResult = await (ComputeCenter.get_instance().do_llm_completion(
            prompt,
            resp_mode=resp_mode,
            mode_name=self.model_name,
            max_token=max_result_token,
            inner_functions=inner_functions, #NOTICE: inner_function in prompt can be a subset of get_inner_function
            timeout=self.timeout))

        if task_result.result_code != ComputeTaskResultCode.OK:
            logger.error(f"llm compute error:{task_result.error_str}")
            return task_result

        inner_func_call_node = None

        result_message : dict = task_result.result.get("message")
        if result_message:
            inner_func_call_node = result_message.get("function_call")
            if inner_func_call_node:
                func_msg = copy.deepcopy(result_message)
                del func_msg["tool_calls"]#TODO: support tool_calls?
                prompt.messages.append(func_msg)


        if inner_func_call_node:
            return await self._execute_inner_func(inner_func_call_node,prompt,stack_limit-1)
        else:
            return task_result

    async def process(self,input:Dict) -> LLMResult:
        if self.enable_json_resp:
            resp_mode = "json"
        else:
            resp_mode = "text"

        # Action define in prompt, will be execute after llm compute
        prompt = await self.prepare_prompt(input)
        if prompt is None:
            logger.warn(f"prepare_prompt return None, break llm_process")
            return LLMResult.from_error_str("prepare_prompt return None")
        
        max_result_token = self.max_token - ComputeCenter.llm_num_tokens(prompt,self.model_name)
        #if max_result_token < MIN_PREDICT_TOKEN_LEN:
        #    return LLMResult.from_error_str(f"prompt too long,can not predict")
        logger.info(f"do_llm_completion with max_result_token:{max_result_token},resp_mode:{resp_mode},prompt:{prompt}")
        task_result: ComputeTaskResult = await (ComputeCenter.get_instance().do_llm_completion(
                prompt,
                resp_mode=resp_mode,
                mode_name=self.model_name,
                max_token=max_result_token,
                inner_functions=prompt.inner_functions, #NOTICE: inner_function in prompt can be a subset of get_inner_function
                timeout=self.timeout))

        if task_result.result_code != ComputeTaskResultCode.OK:
            err_str = f"do_llm_completion error:{task_result.error_str}"
            logger.error(err_str)
            return LLMResult.from_error_str(err_str)

        result_message = task_result.result.get("message")
        inner_func_call_node = None
        if result_message:
            inner_func_call_node = result_message.get("function_call")

        if inner_func_call_node:
            call_prompt : LLMPrompt = copy.deepcopy(prompt)
            func_msg = copy.deepcopy(result_message)
            del func_msg["tool_calls"]
            call_prompt.messages.append(func_msg)
            task_result = await self._execute_inner_func(inner_func_call_node,call_prompt)

        # parse task_result to LLM Result
        if self.enable_json_resp:
            try:
                llm_result = LLMResult.from_json_str(task_result.result_str)
            except Exception as e:
                logger.error(f"parse llm result error:{e}")
                llm_result = LLMResult.from_str(task_result.result_str)
        else:
            llm_result = LLMResult.from_str(task_result.result_str)

        # use action to save history?
        await self.on_post_llm_process(llm_result.action_list,input,llm_result)

        return llm_result


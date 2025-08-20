
from typing import Optional
from ..llm_base import *

import logging
logger = logging.getLogger(__name__)



# 对长的，消耗的的`AI` 计算任务进行封装
# 因为这些任务可能都比较长，所以根据配置默认都会创建Task，通过TaskId可以反复查看结果
class ComputeCenter:
    _instance = None
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = ComputeCenter()
        return cls._instance

    def __init__(self) -> None:
        self.is_start = False
        self.task_queue = Queue()
        self.is_start = False
        self.compute_nodes = {}

    
    async def llm_num_tokens_from_text(self,text:str,model:str = None) -> int:
        pass

    async def llm_num_tokens(self,prompt: LLMPrompt, model_name: str = None) -> int:
        return ComputeCenter.llm_num_tokens_from_text(prompt.as_str(), model_name)

    async def do_llm_completion(self, prompt: LLMPrompt,resp_mode:str="text", mode_name: Optional[str]=None, max_token:int=0, inner_functions=None, timeout=60) -> str:
        pass

    async def do_text_embedding(self,input:str,model_name:Optional[str] = None) -> [float]:
        pass

    async def do_image_embedding(self,input:ObjectID,model_name:Optional[str] = None) -> [float]:
        pass

    async def do_text_to_speech(self,input:str,language_code:Optional[str] = None,gender: Optional[str] = None,
                       age: Optional[str] = None,
                       voice_name: Optional[str] = None,
                       tone: Optional[str] = None,
                       model_name: Optional[str] = None):
        pass

    async def do_speech_to_text(self,
                                audio: str,
                                model: str,
                                prompt: Optional[str],
                                response_format: Optional[str]):
        pass

    async def do_text_2_image(self, prompt:str, model_name:Optional[str] = None, negative_prompt = None) -> ComputeTaskResult:
        pass

    async def do_image_2_text(self, image_path: str, prompt:str, model_name:Optional[str] = None, negative_prompt = None) -> ComputeTaskResult:
        pass


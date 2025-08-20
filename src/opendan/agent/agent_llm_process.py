import os.path

from .chatsession import AIChatSession
from ..utils import video_utils,image_utils

from ..proto.compute_task_test import LLMPrompt,LLMResult,ComputeTaskResult,ComputeTaskResultCode
from ..proto.ai_function import AIFunction,AIAction,ActionNode
from ..proto.agent_msg import AgentMsg,AgentMsgType

from .agent_memory import AgentMemory
from .workspace import AgentWorkspace
from .llm_context import LLMProcessContext,GlobalToolsLibrary, SimpleLLMContext

from ..frame.compute_center import ComputeCenter
from ..knowledge.knowledge_base import BaseKnowledgeGraph

from abc import ABC,abstractmethod
import copy
import json
import datetime
from datetime import datetime
from typing import Any, Callable, Coroutine, Optional,Dict,Awaitable,List
from enum import Enum
import logging

logger = logging.getLogger(__name__)

MIN_PREDICT_TOKEN_LEN = 32

class LLMAgentBaseProcess(BaseLLMProcess):
    def __init__(self) -> None:
        super().__init__()

        self.role_description:str = None
        self.process_description:str = None
        self.reply_format:str = None
        self.context : str = None

        self.workspace : AgentWorkspace = None # If Workspace is not none , enable Agent Tasklist
        self.memory : AgentMemory = None
        self.enable_kb_list : List[str] = None

    async def initial(self,params:Dict = None) -> bool:
        self.memory = params.get("memory")
        if self.memory is None:
            logger.error(f"LLMAgeMessageProcess initial failed! memory not found")
            return False
        self.workspace = params.get("workspace")

        return True
    async def load_default_config(self) -> bool:
        return True


    async def load_from_config(self, config: dict,is_load_default=True) -> Coroutine[Any, Any, bool]:
        if is_load_default:
            await self.load_default_config()

        if await super().load_from_config(config) is False:
            return False

        self.role_description = config.get("role_desc")
        if self.role_description is None:
            logger.error(f"role_description not found in config")
            return False

        if config.get("process_description"):
            self.process_description = config.get("process_description")

        if config.get("reply_format"):
            self.reply_format = config.get("reply_format")

        if config.get("context"):
            self.context = config.get("context")

        if config.get("knowledge_grpah_introduce"):
            self.knowledge_grpah_introduce = config.get("knowledge_grpah_introduce")

        self.llm_context = SimpleLLMContext()
        if config.get("llm_context"):
            self.llm_context.load_from_config(config.get("llm_context"))

    def prepare_knowledge_grpah_prompt(self) -> Dict:
        result = {}
 
        result["introduce"] = BaseKnowledgeGraph.get_kb_default_desc_str()
        result["knowledge_graph_list"] = {}
        have_kb = False

        if self.memory.enable_knowledge_graph:
            result["knowledge_graph_list"][self.memory.knowledge_graph.kb_id] = self.memory.knowledge_graph.get_description()
            have_kb = True
        
        if self.enable_kb_list:
            for kb_id in self.enable_kb_list:
                kb = BaseKnowledgeGraph.get_kb(kb_id) 
                if kb:
                    have_kb = True
                    result["knowledge_graph_list"][kb_id] = kb.get_description()
                else:
                    logger.error(f"knowledge base {kb_id} not found")
        
        if have_kb is False:
            return None
        
        return result
    
   
    def prepare_role_system_prompt(self,context_info:Dict) -> Dict:
        system_prompt_dict = {}

        system_prompt_dict["role_description"] = self.role_description
        system_prompt_dict["process_rule"] = self.process_description
        system_prompt_dict["reply_format"] = self.reply_format

        kb_prompt = self.prepare_knowledge_grpah_prompt()
        if kb_prompt:
            system_prompt_dict["knowledge_graph"] = kb_prompt

        ## Context
        if self.context:
            context = self._format_content_by_env_value(self.context,context_info)
            system_prompt_dict["context"] = context
            #prompt.append_system_message(context)

        system_prompt_dict["support_actions"] = self.get_action_desc()

        return system_prompt_dict

    def prepare_inner_function_context_for_exec(self,inner_func_name:str,parameters:Dict):
        parameters["_workspace"] = self.workspace

    def get_action_desc(self) -> Dict:
        result = {}
        actions_list = []

        actions_list.extend(self.llm_context.get_all_ai_action())
    
        for action in actions_list:
            result[action.get_name()] = action.get_description()
 
        return result

    async def get_inner_function_for_exec(self,func_name:str) -> AIFunction:
        return self.llm_context.get_ai_function(func_name)

    async def _execute_actions(self,actions:List[ActionNode],action_params:Dict):
        for action_item in actions:
            op : AIAction = self.llm_context.get_ai_action(action_item.name)
            if op:
                if action_item.parms is None:
                    action_item.parms = {}

                real_parms = {**action_params,**action_item.parms}

                action_item.parms["_result"] = await op.execute(real_parms)
                action_item.parms["_end_at"] = datetime.now()
            else:
                logger.warn(f"action {action_item.name} not found")
                return False


class AgentMessageProcess(LLMAgentBaseProcess):
    def __init__(self) -> None:
        super().__init__()
        self.mutil_model = None
        self.enable_media2text = False
        self.is_mutil_model = False
        self.asr_model = None
        self.tts_model = None

    async def load_default_config(self) -> bool:
        return True

    async def load_from_config(self, config: dict,is_load_default=True) -> Coroutine[Any, Any, bool]:
        if is_load_default:
            await self.load_default_config()

        if await super().load_from_config(config) is False:
            return False

        self.enable_media2text = config.get('enable_media2text', 'false').lower() in ('true', '1', 't', 'y', 'yes')

        if config.get("mutil_model"):
            self.mutil_model = config.get("mutil_model")

        self.asr_model = config.get("asr_model")
        self.tts_model = config.get("tts_model")

    def get_llm_model_name(self) -> str:
        if self.is_mutil_model:
            return self.mutil_model
        else:
            return self.model_name

    def check_and_to_base64(self, image_path: str) -> str:
        if image_utils.is_file(image_path):
            return image_utils.to_base64(image_path, (1024, 1024))
        else:
            return image_path

    async def get_prompt_from_msg(self,msg:AgentMsg) -> LLMPrompt:
        msg_prompt = LLMPrompt()
        self.is_mutil_model = False
        if msg.is_image_msg():
            if self.enable_media2text:
                logger.error(f"enable_media2text is not supported yet")
            else:
                image_prompt, images = msg.get_image_body()
                if image_prompt is None:
                    msg_prompt.messages = [{"role": "user", "content": [{"type": "image_url", "image_url": {"url": self.check_and_to_base64(image)}} for image in images]}]
                else:
                    content = [{"type": "text", "text": image_prompt}]
                    content.extend([{"type": "image_url", "image_url": {"url": self.check_and_to_base64(image)}} for image in images])
                    msg_prompt.messages = [{"role": "user", "content": content}]

                if self.mutil_model:
                    self.is_mutil_model = True
                else:
                    logger.warning(f"mutil_model is not set!")

        elif msg.is_video_msg():
            if self.enable_media2text:
                logger.error(f"enable_media2text is not supported yet")
            else:
                video_prompt, video = msg.get_video_body()
                frames = video_utils.extract_frames(video, (1024, 1024))
                audio_file = os.path.splitext(video)[0] + ".mp3"
                video_utils.extract_audio(video, audio_file)

                voice_content = None
                if self.asr_model is not None:
                    resp = await (ComputeCenter.get_instance().do_speech_to_text(audio_file, model=self.asr_model, prompt=None, response_format="text"))
                    if resp.result_code == ComputeTaskResultCode.OK:
                        voice_content = resp.result_str

                content = []
                if video_prompt is not None:
                    content.append({"type": "text", "text": video_prompt})
                if voice_content is not None and voice_content != "":
                    content.append({"type": "text", "text": f"Voice content in video:{voice_content}"})

                content.extend([{"type": "image_url", "image_url": {"url": frame}} for frame in frames])
                msg_prompt.messages = [{"role": "user", "content": content}]
                if self.mutil_model:
                    self.is_mutil_model = True
                else:
                    logger.warning(f"mutil_model is not set!")
        elif msg.is_audio_msg():
            if self.enable_media2text:
                logger.error(f"enable_media2text is not supported yet")
            else:
                prompt, audio_file = msg.get_audio_body()
                resp = await (ComputeCenter.get_instance().do_speech_to_text(audio_file, model=self.asr_model, prompt=None, response_format="text"))
                if resp.result_code != ComputeTaskResultCode.OK:
                    error_resp = msg.create_error_resp(resp.error_str)
                    return error_resp
                else:
                    if prompt == "":
                        msg.body = resp.result_str
                        msg_prompt.messages = [{"role":"user","content":resp.result_str}]
                    else:
                        msg.body = f"{prompt}\nVoice content:{resp.result_str}"
                        msg_prompt.messages = [{"role":"user","content": prompt}, {"role": "user", "content": f"Voice content:{resp.result_str}"}]
        else:
            msg_prompt.messages = [{"role":"user","content":msg.body}]

        return msg_prompt

    async def sender_info(self,msg:AgentMsg)->str:
        sender_id = msg.sender
        #TODO Is sender an agent?
        return await self.memory.get_contact_summary(sender_id)

    async def load_chatlogs(self,msg:AgentMsg,max_length_by_token:int)->str:
        ## like
        #sender,[2023-11-1 12:00:00]
        #content
        return await self.memory.load_chatlogs(msg,max_length_by_token)

    async def get_chat_summary(self,msg:AgentMsg)->str:
        return await self.memory.get_chat_summary(msg)



    async def get_extend_known_info(self,msg:AgentMsg,prompt:LLMPrompt)->str:
        return None

    async def prepare_prompt(self,input:Dict) -> LLMPrompt:
        prompt = LLMPrompt()
        # User Prompt
        ## Input Msg
        msg : AgentMsg = input.get("msg")
        context_info = input.get("context_info")
        if msg is None:
            logger.error(f"LLMAgeMessageProcess prepare_prompt failed! input msg not found")
            return None
        msg_prompt = await self.get_prompt_from_msg(msg)
        if msg_prompt is None:
            logger.error(f"LLMAgeMessageProcess prepare_prompt failed! get_prompt_from_msg return None")
            return None
        prompt.append(msg_prompt)

        ## 通用的角色相关的系统提示词
        system_prompt_dict = self.prepare_role_system_prompt(context_info)

        ## 已知信息
        known_info = {}
        #prompt.append_system_message(self.known_info_tips)
        ### 信息发送者资料
        known_info["sender_info"] = await self.sender_info(msg)
        #prompt.append_system_message(await self.sender_info(self,msg))

        system_prompt_dict["known_info"] = known_info

        prompt.inner_functions =LLMProcessContext.aifunctions_to_inner_functions(self.llm_context.get_all_ai_functions())
        if self.workspace:
            #TODO eanble workspace functions?
            logger.info(f"workspace is not none,enable workspace functions")


        ### 根据Token Limit加载聊天记录
        remain_token = self.get_remain_prompt_length(prompt,json.dumps(system_prompt_dict,ensure_ascii=False))
        chat_record,is_all = await self.load_chatlogs(msg,remain_token - self.chat_summary_token_len)
        if chat_record:
            if len(chat_record) > 4:
                known_info["chat_record"] = chat_record

            if not is_all :
                ### 如果出触发了Token Limit,则删除几条信息后，加载summary （summary的长度基本是固定的）
                summary = await self.get_chat_summary(msg)
                if summary:
                    if len(summary) > 4:
                        known_info["chat_summary"] = summary

        # TODO: extend known info
        #prompt.append_system_message(await self.get_extend_known_info(msg,prompt))
         
        prompt.append_system_message(json.dumps(system_prompt_dict,ensure_ascii=False))
        return prompt


    async def post_llm_process(self,actions:List[ActionNode],input:Dict,llm_result:LLMResult) -> bool:
        msg:AgentMsg = input.get("msg")
        if msg.msg_type == AgentMsgType.TYPE_GROUPMSG:
            resp_msg = msg.create_group_resp_msg(self.memory.agent_id,llm_result.resp)
        else:
            resp_msg = msg.create_resp_msg(llm_result.resp)

        if llm_result.raw_result is not None:
            llm_result.raw_result["_resp_msg"] = resp_msg

        action_params = {}
        action_params["_input"] = input
        action_params["_memory"] = self.memory
        action_params["_workspace"] = self.workspace
        action_params["_resp_msg"] = resp_msg
        action_params["_llm_result"] = llm_result
        action_params["_agentid"] = self.memory.agent_id
        action_params["_start_at"] = datetime.now()

        await self._execute_actions(actions,action_params)

        chatsession = self.memory.get_session_from_msg(msg)
        chatsession.append(msg)
        chatsession.append(resp_msg)

        return True

class AgentSelfThinking(LLMAgentBaseProcess):
    def __init__(self) -> None:
        super().__init__()
        

    async def load_from_config(self, config: dict) -> Coroutine[Any, Any, bool]:
        if await super().load_from_config(config) is False:
            return False

    async def _load_chat_history(self,token_limit:int):
        chat_history = {}
        session_list = AIChatSession.list_session(self.memory.agent_id ,self.memory.memory_db)
        total_read_msg = 0
        for session_id in session_list:
            chatsession = AIChatSession.get_session_by_id(session_id,self.memory.memory_db)
            session_history = {}
            session_history["summary"] = chatsession.summary
            session_history["id"] = chatsession.session_id
            token_limit -= ComputeCenter.llm_num_tokens_from_text(chatsession.summary,self.model_name)
            read_history_msg = 0
            
            if token_limit > 8:
                # load session chat history
                cur_pos = chatsession.summarize_pos
                messages = chatsession.read_history(0,cur_pos,"natural") # read
                history_str = ""
                for msg in messages:
                    read_history_msg += 1
                    total_read_msg += 1
                    cur_pos += 1
                    dt = datetime.fromtimestamp(float(msg.create_time))
                    formatted_time = dt.strftime('%y-%m-%d %H:%M:%S')
                    record_str = f"{msg.sender},[{formatted_time}]\n{msg.body}\n"
                    token_limit -= ComputeCenter.llm_num_tokens_from_text(record_str,self.model_name)
                    if token_limit < 8:
                        break

                    history_str = history_str + record_str

                if ComputeCenter.llm_num_tokens_from_text(history_str,self.model_name) > self.chat_summary_token_len:
                    session_history["history"] = history_str
                    chat_history[session_id] = session_history
                    chatsession.summarize_pos = cur_pos

            else:
                logger.info(f"load_chat_history reach token limit,load {total_read_msg} history messages.")
                return chat_history
            
        if total_read_msg < 2:
            logger.info(f"load_chat_history: no history messages,return NONE")
            return None
        
        return chat_history   
                

    async def prepare_prompt(self,input:Dict) -> LLMPrompt:
        prompt = LLMPrompt()

        context_info = input.get("context_info")
        
        system_prompt_dict = self.prepare_role_system_prompt(context_info)

        # Known_info is the SESSION summary of the existence, the current task work record summary,
        token_remain = self.get_remain_prompt_length(prompt,json.dumps(system_prompt_dict,ensure_ascii=False))
        chat_history = await self._load_chat_history(token_remain)
        if chat_history is None:
            logger.info(f"prepare_prompt: no history messages,return NONE")
            return None
        
        prompt.inner_functions =LLMProcessContext.aifunctions_to_inner_functions(self.llm_context.get_all_ai_functions())
        
        prompt.append_system_message(json.dumps(system_prompt_dict,ensure_ascii=False))
        prompt.append_user_message(json.dumps(chat_history,ensure_ascii=False))
        return prompt 

    async def post_llm_process(self,actions:List[ActionNode],input:Dict,llm_result:LLMResult) -> bool:
        action_params = {}
        action_params["_input"] = input
        action_params["_memory"] = self.memory
        action_params["_workspace"] = self.workspace
        action_params["_llm_result"] = llm_result
        action_params["_agentid"] = self.memory.agent_id
        action_params["_start_at"] = datetime.now()
        try:
            if await self._execute_actions(actions,action_params) is False:
                result_str = "execute action failed!"
        except Exception as e:
            logger.error(f"execute action failed! {e}")
            result_str = "execute action failed!,error:" + str(e)

class AgentSelfLearning(BaseLLMProcess):
    def __init__(self) -> None:
        super().__init__()

    async def load_from_config(self, config: dict) -> Coroutine[Any, Any, bool]:
        if await super().load_from_config(config) is False:
            return False

    async def prepare_prompt(self) -> LLMPrompt:
        prompt = LLMPrompt()
        pass

    async def get_inner_function_for_exec(self,func_name:str) -> AIFunction:
        pass

    async def post_llm_process(self,actions:List[ActionNode]) -> bool:
        pass

class AgentSelfImprove(BaseLLMProcess):
    def __init__(self) -> None:
        super().__init__()



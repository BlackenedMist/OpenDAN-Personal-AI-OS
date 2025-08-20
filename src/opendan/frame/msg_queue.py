
import logging
from ..agent_msg import *

logger = logging.getLogger(__name__)

class MsgQueue:
    @classmethod
    def get_msg_queue(cls,queue_id:str):
        pass

    def __init__(self) -> None:
        pass

    async def pop_message(self,timeout:int = 10) -> AgentMsg:
        pass

    async def post_message(self,msg:AgentMsg) -> bool:
        pass

    async def reply_message(self,org_msg_id:str,resp:AgentMsg) -> None:
        pass

    async def get_message_reply(self,msg_id:str,timeout:int = 10) -> AgentMsg:
        pass

    async def send_message(self,msg:AgentMsg,target_id = None, real_sender=None) -> AgentMsg:
        pass

   
import sys
import os
current_dir = os.path.dirname(__file__)
sys.path.append(current_dir + '/../../')


from opendan.agent import Agent
from opendan import MsgQueue

async def jarvis_main():
    # init agent by config
    agent_config_path = os.path.join(current_dir, 'jarvis.toml')
    jarvis_agent = Agent(agent_config_path)

    # # main loop: get agent_msg from msg queue
    # # process msg
    # msg_queue = MsgQueue()
    # msg_queue.start("agent.jarvis")
    # while True:
    #     msg = msg_queue.get()
    #     msg_resp = agent.process_msg(msg)
    #     msg_queue.reply(msg_resp)
    msg_queue = MsgQueue("agent.jarvis")
    while True:
        msg = await msg_queue.pop_message()
        msg_resp = await jarvis_agent.process_msg(msg)
        await msg_queue.reply_message(msg.msg_id,msg_resp)


if __name__ == "__main__":
    jarvis_main();
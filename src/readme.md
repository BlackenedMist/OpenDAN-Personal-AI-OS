# 新目录说明

## agents
基于opendan框架实现的 完整agent, 这里每个agnet都是一个可以独立运行的进程（容器），可以被安装在buckyos中
opendan还计划定义只有配置的agent, 只包含从自然语言出发的基本配置，不同的agent runtime都可以选择支持这种agent,并决定在一个runtime(进程中)是否同时运行多个agent


## opendan
Agent开发框架，实现了基于opendan理念的Agent.
frame目录是对buckyos相关服务的封装（转调用buckyos-py-sdk), 为了一些简单场景的开发调试方便，这些服务可能有一个简单的实现（dev模式)
**openDAN框架依赖buckyos**


### llm_process
对llm行为的最浅层的封装。添加了一些必要的基础概念

### agent 
opendan的agent框架（含多agent协作框架workflow)。定义了agent的基本行为逻辑


## services
基于OpenDAN框架构造的,运行在buckyos上的系统服务，以支持buckyos成为aios。
buckyos将于beta1版本开始，默认集成openDAN runtime service. 该service会使用python为buckyos提供如下功能
- 基于msg_tunnel框架，从tg / discord /slack 接收/发送消息。
- 启用一些 内置 agent
- 启用一些 内置 workflow(agent工作流)

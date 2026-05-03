import asyncio
import time
from typing import Callable
from langchain.agents import create_agent
from langchain.agents.middleware import ModelRequest, ModelResponse, wrap_model_call
from langchain.chat_models import init_chat_model
import os

from langchain_core.messages import HumanMessage, BaseMessage, SystemMessage, AIMessageChunk
from langchain.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.state import CompiledStateGraph


@tool(description="查找我的基本信息")
def who_am_i()->dict:
    return {"name":"XXX"}





## 两个线程池，不同的线程池是不同的model，预装5个agent，一个任务，执行失败了，换一个池

os.environ["model"]="deepseek-v4-flash"
os.environ["base_url"]="https://api.deepseek.com"
os.environ["api_key"]="sk-6e3e5a4d8535442aa83fe1983affe742"



def select_relevant_tools(state, runtime):
    return "todo"

@wrap_model_call
def select_tools(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse],
) -> ModelResponse:
    """Middleware to select relevant tools based on state/context."""
    # Select a small, relevant subset of tools based on state/context
    relevant_tools = select_relevant_tools(request.state, request.runtime)
    return handler(request.override(tools=relevant_tools))



def create_model1_agent():
    model = init_chat_model(os.environ.get("model"),
                            base_url=os.environ.get("base_url"),
                            api_key=os.environ.get("api_key"))
    agent = create_agent(model=model,tools=[who_am_i],
                         middleware=[select_tools]
                         )
    return agent

def create_model2_agent():
    model = init_chat_model(os.environ.get("model"),
                            base_url=os.environ.get("base_url"),
                            api_key=os.environ.get("api_key"),)
    agent = create_agent(model=model,tools=[who_am_i])
    return agent
from agent_pool2 import ObjectPool
agent1_pool = ObjectPool(create_model1_agent,max_size=1)
agent2_pool = ObjectPool(create_model2_agent,max_size=1)

async def askquestion(messages:list[BaseMessage]):
    retry_limit = 5
    retry_interval = 10
    execed: bool = False

    while not execed and retry_limit > 0:
        pools = [agent1_pool, agent2_pool]
        final_output=None

        for pool in pools:
            with pool.acquire() as agent:
                if not agent:
                    continue
                else:
                    execed = True
                    # agent会有前朝的记忆
                    memory = InMemorySaver()
                    final_output = await runner(agent, messages,memory)
                    break
                    ## todo 重试判断每分钟输出token超出
        if not execed:
            retry_limit = retry_limit - 1
            await asyncio.sleep(retry_interval)

    if not execed:
        print("还是没有获得执行机会")


    return (execed, final_output)




async def runner(agent:CompiledStateGraph, messages:list[BaseMessage], memory:InMemorySaver)->str:
    agent.checkpointer=memory

    print(f"========开始处理问题{messages}")
    """stream_mode values每一步都返回完整消息列表"""
    # full_msg = []
    # async for chunk in agent.astream(
    #        input={"messages":messages},
    #        config={"configurable": {"thread_id": "1"}},
    #        stream_mode="values"):
    #    ##每一次都拿完整消息列表
    #    full_msg = chunk["messages"]
    ### 最后一条消息就是最终消息
    # latest=full_msg[-1]
    # print(latest)
    """stream_mode updates只返回当前节点的增量消息"""
    # final_msg=None
    # async for chunk in agent.astream(
    #        input={"messages":messages},
    #        config={"configurable": {"thread_id": "1"}},
    #        stream_mode="updates"):
    #    for node,data in chunk.items():
    #        # ? 一个节点还能返回多个？为什么是数组
    #        new_msg = data["messages"][-1]
    #        print(new_msg)
    #        final_msg = new_msg
    ### 最终消息
    # print(final_msg)
    """stream_mode messages token级别最细，需要手动累加，比较复杂，需要通过工具调用来分割来判断是否是新的AIMESSAGE"""
    ai_rounds = []
    current_round_chunk: AIMessageChunk | None = None
    async for chunk, meta in agent.astream(
            input={"messages": messages},
            config={"configurable": {"thread_id": "1"}},
            stream_mode="messages"):
        if not isinstance(chunk, AIMessageChunk):
            continue
        if not chunk.tool_calls:
            if current_round_chunk is None:
                current_round_chunk = chunk
            else:
                current_round_chunk += chunk
        else:
            if current_round_chunk:
                ai_rounds.append(current_round_chunk)
                current_round_chunk = None

    if current_round_chunk:
        ai_rounds.append(current_round_chunk)
    final_answer = ai_rounds[-1] if ai_rounds else None
    print(final_answer.content)
    return final_answer.content

async def checkpoints():
    sys_msg = SystemMessage("你是一位金融分析专家,输出限制在40个字符，在处理问题前，需要先通过工具获取我的信息")
    ques_msg = [
        HumanMessage("招银网络科技公司的基本情况怎么样"),
        HumanMessage("菜鸟公司的基本情况怎么样"),
        HumanMessage("饿了吗公司的基本情况怎么样"),
    ]

    tasks = [askquestion([sys_msg, msg]) for msg in ques_msg]

    results = await (asyncio.gather(*tasks))
    for res in results:
        pass
    print("all done")




if __name__ == "__main__":
    asyncio.run(checkpoints())


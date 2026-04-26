import asyncio

from _testcapi import awaitType
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
import os

from langchain_core.messages import HumanMessage, BaseMessage, SystemMessage, AIMessageChunk
from langgraph.checkpoint.memory import InMemorySaver

async def askquestion(messages:list[BaseMessage]):
    model = init_chat_model("gpt-5.4-mini",
                            base_url="https://api.chatanywhere.tech/v1",
                            api_key="sk-E1LDx9RPXp4bfejIy80YGKhVI0RjOeAgpg0KgzWAGGWx28sx")
    agent = create_agent(model=model, checkpointer=InMemorySaver())
    """stream_mode values每一步都返回完整消息列表"""
    #full_msg = []
    #async for chunk in agent.astream(
    #        input={"messages":messages},
    #        config={"configurable": {"thread_id": "1"}},
    #        stream_mode="values"):
    #    ##每一次都拿完整消息列表
    #    full_msg = chunk["messages"]
    ### 最后一条消息就是最终消息
    #latest=full_msg[-1]
    #print(latest)
    """stream_mode updates只返回当前节点的增量消息"""
    #final_msg=None
    #async for chunk in agent.astream(
    #        input={"messages":messages},
    #        config={"configurable": {"thread_id": "1"}},
    #        stream_mode="updates"):
    #    for node,data in chunk.items():
    #        # ? 一个节点还能返回多个？为什么是数组
    #        new_msg = data["messages"][-1]
    #        print(new_msg)
    #        final_msg = new_msg
    ### 最终消息
    #print(final_msg)
    """stream_mode messages token级别最细，需要手动累加，比较复杂，需要通过工具调用来分割来判断是否是新的AIMESSAGE"""
    ai_rounds = []
    current_round_chunk:AIMessageChunk | None = None
    async for chunk, meta in agent.astream(
            input={"messages":messages},
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
    return final_answer.content


async def checkpoints():
    sys_msg = SystemMessage("你是一位金融分析专家")
    ques_msg = [HumanMessage("招银网络科技公司的基本情况怎么样"),
                HumanMessage("湖南卫视公司的基本情况怎么样"),
                HumanMessage("阿里巴巴的基本情况怎么样"),
                HumanMessage("饿了么公司的基本情况怎么样"),
                HumanMessage("同花顺的基本情况怎么样")]

    tasks = [askquestion([sys_msg, msg]) for msg in ques_msg]

    result = await (asyncio.gather(*tasks))
    for oneresult in result:
        print(oneresult)




if __name__ == "__main__":
    asyncio.run(checkpoints())


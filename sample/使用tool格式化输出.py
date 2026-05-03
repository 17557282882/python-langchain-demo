'''怎么才能把这个做的通用呢，类似输入一个类型，和上下文，输出对象'''
from typing import Literal

from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END, MessagesState
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field


@tool
def get_weather(city: Literal["nyc", "sf"]):

    """Use this to get weather information."""
    if city == "nyc":
        return "It is cloudy in NYC, with 5 mph winds in the North-East direction and a temperature of 70 degrees"
    elif city == "sf":
        return "It is 75 degrees and sunny in SF, with 3 mph winds in the South-East direction"
    else:
        raise AssertionError("Unknown city")

class WeatherResponse(BaseModel):
    """Respond to the user with this"""

    temperature: float = Field(description="The temperature in fahrenheit")
    wind_directon: str = Field(description="The direction of the wind in abbreviated form")
    wind_speed: float = Field(description="The speed of the wind in km/h")

class AgentState(MessagesState):
    # Final structured response from the agent
    final_response: WeatherResponse



# Force the model to use tools by passing tool_choice="any"
model = init_chat_model("gpt-5.4-mini",
                            base_url="https://api.chatanywhere.tech/v1",
                            api_key="sk-E1LDx9RPXp4bfejIy80YGKhVI0RjOeAgpg0KgzWAGGWx28sx")

tools = [get_weather, WeatherResponse]
model_with_response_tool = model.bind_tools(tools, tool_choice="any")


def call_model(state: AgentState):
    response = model_with_response_tool.invoke(state["messages"])
    # We return a list, because this will get added to the existing list
    return {"messages": [response]}


# Define the function that responds to the user
def respond(state: AgentState):
    weather_tool_call = state["messages"][-1].tool_calls[0]
    response = WeatherResponse(**weather_tool_call["args"])
    tool_message = {
        "type": "tool",
        "content": "Here is your structured response",
        "tool_call_id": weather_tool_call["id"],
    }
    # We return the final answer
    return {"final_response": response, "messages": [tool_message]}


def should_continue(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]
    if (
        len(last_message.tool_calls) == 1
        and last_message.tool_calls[0]["name"] == "WeatherResponse"
    ):
        return "respond"
    else:
        return "continue"


# Define a new graph
workflow = StateGraph(AgentState)

# Define the two nodes we will cycle between
workflow.add_node("agent", call_model)
workflow.add_node("respond", respond)
workflow.add_node("tools", ToolNode(tools))

workflow.set_entry_point("agent")

# We now add a conditional edge
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "continue": "tools",
        "respond": "respond",
    },
)

workflow.add_edge("tools", "agent")
workflow.add_edge("respond", END)
graph = workflow.compile()

if __name__ == "__main__":
    answer = graph.invoke(input={"messages": [("human", "what's the weather in SF?")]})[
        "final_response"
    ]
    print(answer)
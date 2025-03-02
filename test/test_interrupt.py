from typing import Optional, TypedDict
import uuid
from langgraph.types import interrupt
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

class State(TypedDict):
    foo: str
    human_value: Optional[str]

def node(state: State):
    answer = interrupt("what is your age?")  # 中断并请求用户输入
    print(f"> Received an input from the interrupt: {answer}")
    return {"human_value": answer}


builder = StateGraph(State)
builder.add_node("node", node)
builder.add_edge(START, "node")
checkpointer = MemorySaver()
graph = builder.compile(checkpointer=checkpointer)

config = {"configurable": {"thread_id": uuid.uuid4()}}
for chunk in graph.invoke({"foo": "abc"}, config):
    print(chunk)
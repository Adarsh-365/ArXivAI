from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage # Import this

import os
from dotenv import load_dotenv

load_dotenv()
from model import agent1

# Graph state
class State(TypedDict):
    query: str
    result: str
   

# Nodes
def agentfunction(state: State):
    """First LLM call to generate initial joke"""
    # print(state)s
    inner_input = {"messages": [HumanMessage(content=state['query'])]}
    msg = agent1.invoke(inner_input)
    # print(msg)
    
    return {"result": msg["messages"][-1].content}



# Build workflow
workflow = StateGraph(State)

# Add nodes
workflow.add_node("agent", agentfunction)


# Add edges to connect nodes
workflow.add_edge(START, "agent")

workflow.add_edge("agent", END)

# Compile
chain = workflow.compile()


# Invoke
state = chain.invoke({"query": "list 5 paper pdf link  and list of title of topic mixture of expert"})

print(state["result"])

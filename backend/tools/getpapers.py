# from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from tools.arxivetool import get_arxiv_papers




from model import llm
llm_with_tools = llm.bind_tools([get_arxiv_papers])

def getpapers(query):

    # 3. Call LLM (It will return the ARGUMENTS, not the result)
    
    response_msg = llm_with_tools.invoke(query)

    print(response_msg)
    # 4. Check if LLM wants to call the tool
    if response_msg.tool_calls:
        # Extract arguments provided by LLM
        tool_call = response_msg.tool_calls[0]
        func_args = tool_call["args"]
        
        # print(f"LLM decided to call function with args: {func_args}")
        
        # 5. Execute Manually (Output stays in Python variable, never goes to LLM)
        huge_result = get_arxiv_papers.invoke(func_args)
        
        # print(f"Result Length: {len(huge_result)}")
        # print("Done. The LLM never saw the huge data.")
    else:
        print("LLM didn't call the tool. It said:", response_msg.content)
    return huge_result
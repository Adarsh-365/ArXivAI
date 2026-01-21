from langchain_google_genai import ChatGoogleGenerativeAI
import os
# from langgraph.prebuilt import create_react_agent
from langchain.agents import create_agent
from tools.arxivetool import get_arxiv_papers
import os
from dotenv import load_dotenv

load_dotenv()
# Set your API key
os.environ["GOOGLE_API_KEY"] = ""


# Initialize the model

# Use "gemini-2.5-flash" for speed or "gemini-2.5-pro" for complex reasoning
# llm = ChatGoogleGenerativeAI(
#     model="gemini-2.5-flash",
#     temperature=0.7,
#     max_tokens=None,
#     timeout=None,
#     max_retries=2,
# )

from langchain_groq import ChatGroq


llm = ChatGroq(
    model="llama-3.1-8b-instant",
 
)
from pydantic import BaseModel, Field


def simplechat(query):
    messages = [
(
    "system",
    """You are a technical documentation assistant. Answer queries strictly based on the provided context.

    Rules:
    1. **For "What is..." questions:** Synthesize a clear, concise definition or summary from the text.
    2. **For "List/Who/When" questions:** Extract the specific entities (e.g., Authors, Dates) without conversational filler.
    3. **Accuracy:** Do not use outside knowledge. If the answer is not in the chunks, say "Not found in context."
    4. **References:** Do not treat the 'References' section as part of the paper's content/authors.
    5. **Format:** Use Markdown (bullet points for lists, bold for key terms).
    """
),
    ("human", query),
]
    chat_completion = llm.invoke(messages)
    return chat_completion.content
    


# 1. The Output Schema (Two lists as requested)
class ResponseFormat(BaseModel):
    paper_names: list[str] = Field(
        description="List of paper titles extracted from the tool output"
    )
    pdf_links: list[str] = Field(
        description="List of PDF URLs extracted from the tool output"
    )

# 2. The System Instruction (Tailored for your specific JSON output)
system_instruction = """
You are a research assistant.
1. The tool returns a dictionary of papers. You must parse this JSON data.
2. Iterate through the values of the dictionary:
   - Extract the value of the key "title" and add it to the 'paper_names' list.
   - Extract the value of the key "pdf_url" and add it to the 'pdf_links' list.
3. STRICT REQUIREMENTS:
   - The 'paper_names' list and 'pdf_links' list must have the same length.
   - Preserve the order (the Nth title must match the Nth link).
   - Do not output any conversational text, only the JSON.
"""

# 3. Create Agent
agent1 = create_agent(
    llm, 
    tools=[get_arxiv_papers], 
    system_prompt=system_instruction, 
    response_format=ResponseFormat
)

tools = [get_arxiv_papers]

# Create the agent
agent1 = create_agent(
    llm, 
    tools, 
    system_prompt=system_instruction, 
    response_format=ResponseFormat
)



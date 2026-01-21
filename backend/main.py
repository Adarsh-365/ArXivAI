from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from tools.getpapers import getpapers
from tools.ragtool import FastTfidfRAG

app = FastAPI()

from model import simplechat

RAGDICT = {}


Memory  = []
# 2. Add the Middleware
# This tells the browser that requests from other origins are allowed.
app.add_middleware(
    CORSMiddleware,
    # allow_origins=["http://localhost:3000"], # Best practice: specific domains only
    allow_origins=["*"],                       # Quick fix: allow ALL origins
    allow_credentials=True,
    allow_methods=["*"],                       # Allow all methods (POST, GET, etc.)
    allow_headers=["*"],                       # Allow all headers
)


# 2. Define the Input Model (Schema)
# This ensures the POST body contains a field called "query" that is a string.
class QueryRequest(BaseModel):
    query: str
    pdfLink: str | None = None
    paperId:str | None = None

# 3. Create the POST endpoint for /ask (legacy)
@app.post("/ask")
def get_answer(request: QueryRequest):
    user_input = request.query + " If count is not given use 100 as count"
    result_text = getpapers(user_input)
    return {"answer": result_text}

# 4. Simple question API used by the frontend
@app.post("/question")
def get_question(request: QueryRequest):
    """Return a simple answer for the given query.

    The frontend posts to this endpoint with a JSON body containing a
    ``query`` field and optionally a ``pdfLink``.  The implementation
    forwards the query to ``getpapers`` and returns the result under the
    ``response`` key, echoing back the provided ``pdfLink`` if present.
    """
    global Memory
    user_input = request.query 
    Memory.append({"USER_QUERY":user_input})
    
    # result_text = getpapers(user_input)
    if request.paperId not in RAGDICT:
        RAGDICT[request.paperId] = FastTfidfRAG(request.pdfLink)
    
    retrieved_docs = RAGDICT[request.paperId].retrieve(user_input)
    # print(docs,len(docs))
    context_str = "\n\n---\n\n".join(retrieved_docs)
    maxn = max(len(Memory),6)
    ques = f"Chat History {Memory[:maxn]} \n\n Context:\n{context_str}\n\nQuestion: {user_input}"
    response = simplechat(ques )
    Memory.append({"BOT_RESPONSE":response})
    # print(response)
    return {"response": str(response)}

# 4. Optional: Block to run the script directly with Python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
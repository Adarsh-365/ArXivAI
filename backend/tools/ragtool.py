import pandas as pd
from rank_bm25 import BM25Okapi
import numpy as np
from langchain_text_splitters import RecursiveCharacterTextSplitter
from arxiv2text import arxiv_to_text

# --- Step 1: Text Extraction and Chunking ---
def extract_text_from_pdf(pdf_url):
    """
    Extracts text from an arXiv PDF URL and splits it into chunks.
    """
    print(f"Extracting text from: {pdf_url}")
    try:
        extracted_text = arxiv_to_text(pdf_url)
    except Exception as e:
        print(f"Error extracting text: {e}")
        return []
    
    # Check if text was actually extracted
    if not extracted_text or not extracted_text.strip():
        print("Failed to extract text or the document is empty.")
        return []

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=200) # Added a small overlap
    texts = text_splitter.split_text(extracted_text)
    
    # --- Crucial Debugging Step ---
    print(f"Successfully split the document into {len(texts)} chunks.")
    return texts

# --- Step 2: RAG Class ---
class FastTfidfRAG:
    def __init__(self, pdf_url: str):
        self.documents = extract_text_from_pdf(pdf_url)
        # Tokenize documents for BM25
        self.tokenized_docs = [doc.split() for doc in self.documents]
        self.bm25 = BM25Okapi(self.tokenized_docs)
        self.index = None
        self.build_index()

    def build_index(self):
        """Build a BM25 index.  The BM25Okapi instance already holds the
        necessary statistics, so this method simply confirms that the
        index is ready.
        """
        print("\nBM25 index ready with", len(self.tokenized_docs), "documents.")

    def retrieve(self, query: str, k: int = 5) -> list:
        if not self.tokenized_docs:
            raise Exception("No documents indexed.")

        query_tokens = query.split()
        scores = self.bm25.get_scores(query_tokens)
        
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        top_indices = [idx for idx, _ in ranked[:k]]
        
        # --- FIX: Always include the first chunk (Header/Abstract) ---
        # Metadata (Authors/Date) is always here. 
        if 0 not in top_indices:
            top_indices.insert(0, 0) # Force add the first chunk
            
        return [self.documents[i] for i in top_indices]

# # --- Step 3: Running the RAG System ---
# if __name__ == '__main__':
#     # Use a valid URL for a real paper
#     # "Attention Is All You Need" paper
#     pdf_url = "https://arxiv.org/pdf/1706.03762.pdf"
    
#     # 1. Extract and chunk the text
#     doc_chunks = extract_text_from_pdf(pdf_url)

#     # 2. Check if we have chunks before proceeding
#     if doc_chunks:
#         # 3. Initialize the RAG system with the chunks
#         rag_system = FastTfidfRAG(documents=doc_chunks)

#         # 4. Perform a query
#         user_query = "what is a transformer model?"
#         retrieved_documents = rag_system.retrieve(user_query, k=5)

#         # 5. Display the results
#         print(f"\nQuery: '{user_query}'")
#         print("\nTop 5 Retrieved Documents:")
#         print("--------------------------")
#         for i, doc in enumerate(retrieved_documents):
#             print(f"Result {i+1}:\n{doc}\n")
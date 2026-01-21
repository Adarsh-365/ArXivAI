import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
import faiss
import numpy as np

class FastTfidfRAG:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words='english', lowercase=True)
        self.index = None
        self.documents = []

    def build_index(self, documents: list):
        """
        Builds the TF-IDF and Faiss index from a list of documents.

        Args:
            documents (list): A list of text documents.
        """
        self.documents = documents
        print("Building TF-IDF index...")
        tfidf_matrix = self.vectorizer.fit_transform(self.documents)
        
        # Convert to a dense matrix for Faiss
        dense_tfidf_matrix = tfidf_matrix.toarray().astype('float32')
        
        print("Building Faiss index...")
        d = dense_tfidf_matrix.shape[1]
        self.index = faiss.IndexFlatL2(d)  # Using L2 distance for similarity
        self.index.add(dense_tfidf_matrix)
        print("Index built successfully.")

    def retrieve(self, query: str, k: int = 5) -> list:
        """
        Retrieves the top-k most relevant documents for a given query.

        Args:
            query (str): The user's query.
            k (int, optional): The number of documents to retrieve. Defaults to 5.

        Returns:
            list: A list of the top-k relevant documents.
        """
        if self.index is None:
            raise Exception("Index has not been built yet. Please call build_index() first.")

        query_vector = self.vectorizer.transform([query]).toarray().astype('float32')
        
        # Search the Faiss index
        distances, indices = self.index.search(query_vector, k)
        
        # Retrieve the documents
        retrieved_docs = [self.documents[i] for i in indices[0]]
        return retrieved_docs

# # --- Example Usage ---
# if __name__ == '__main__':
#     # Sample documents
#     documents = [
#         "The Eiffel Tower is a wrought-iron lattice tower on the Champ de Mars in Paris, France.",
#         "The Great Wall of China is a series of fortifications made of stone, brick, tamped earth, wood, and other materials.",
#         "The Colosseum is an oval amphitheatre in the centre of the city of Rome, Italy.",
#         "The Statue of Liberty is a colossal neoclassical sculpture on Liberty Island in New York Harbor in New York City.",
#         "The Golden Gate Bridge is a suspension bridge spanning the Golden Gate, the one-mile-wide strait connecting San Francisco Bay and the Pacific Ocean."
#     ]

#     # Initialize and build the RAG system
#     rag = FastTfidfRAG()
#     rag.build_index(documents)

#     # User query
#     user_query = "monuments in France"

#     # Retrieve relevant documents
#     retrieved_documents = rag.retrieve(user_query)

#     # In a full RAG system, these retrieved documents would be passed to a language model
#     # along with the query to generate a final answer.
#     print(f"\nQuery: '{user_query}'")
#     print("\nRetrieved Documents:")
#     for doc in retrieved_documents:
#         print(f"- {doc}")
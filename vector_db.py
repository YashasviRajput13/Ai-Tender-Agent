import os
import chromadb
from chromadb.utils import embedding_functions

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chroma_db")

class VectorDB:
    def __init__(self):
        # Create a persistent ChromaDB client
        self.client = chromadb.PersistentClient(path=DB_DIR)
        
        # Use a lightweight sentence-transformer model for embeddings
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        
        # Get or create the collection for tenders
        self.collection = self.client.get_or_create_collection(
            name="tenders",
            embedding_function=self.embedding_function
        )

    def add_tender(self, tender_id: str, text: str, metadata: dict):
        """Add a single tender to the vector DB."""
        try:
            self.collection.upsert(
                documents=[text],
                metadatas=[metadata],
                ids=[tender_id]
            )
            return True
        except Exception as e:
            print(f"Error adding to Vector DB: {e}")
            return False

    def semantic_search(self, query: str, n_results: int = 5):
        """Search the vector DB for relevant tenders."""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            return results
        except Exception as e:
            print(f"Error querying Vector DB: {e}")
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

    def delete_tender(self, tender_id: str):
        """Remove a tender from the vector DB."""
        try:
            self.collection.delete(ids=[tender_id])
        except Exception as e:
            print(f"Error deleting from Vector DB: {e}")

_vector_db_instance = None

def get_vector_db():
    global _vector_db_instance
    if _vector_db_instance is None:
        _vector_db_instance = VectorDB()
    return _vector_db_instance

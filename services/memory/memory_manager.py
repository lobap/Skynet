import os
import chromadb
from chromadb.utils import embedding_functions
import glob

class MemoryManager:
    def __init__(self, persist_path="c:/Dev/Skynet/services/memory/db"):
        self.client = chromadb.PersistentClient(path=persist_path)
        self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        self.collection = self.client.get_or_create_collection(
            name="codebase_knowledge",
            embedding_function=self.embedding_fn
        )

    def index_codebase(self, root_dirs=["c:/Dev/Skynet/backend", "c:/Dev/Skynet/services"]):
        """Scans and indexes all code files in the specified directories."""
        documents = []
        metadatas = []
        ids = []
        
        for root_dir in root_dirs:
            # Recursive search for python and text files
            files = glob.glob(os.path.join(root_dir, "**", "*.py"), recursive=True)
            files.extend(glob.glob(os.path.join(root_dir, "**", "*.txt"), recursive=True))
            files.extend(glob.glob(os.path.join(root_dir, "**", "*.md"), recursive=True))
            
            for file_path in files:
                if "venv" in file_path or "__pycache__" in file_path or ".git" in file_path:
                    continue
                    
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        if not content.strip():
                            continue
                            
                        # Chunking could be improved, but for now we index the whole file or large chunks
                        # For better RAG, we should split by functions/classes.
                        # Keeping it simple: 1 file = 1 doc for now, or simple chunking.
                        
                        documents.append(content)
                        metadatas.append({"source": file_path})
                        ids.append(file_path)
                except Exception as e:
                    print(f"Skipping {file_path}: {e}")

        if documents:
            # Upsert (update or insert)
            # Batching might be needed for large codebases
            batch_size = 100
            for i in range(0, len(documents), batch_size):
                end = min(i + batch_size, len(documents))
                self.collection.upsert(
                    documents=documents[i:end],
                    metadatas=metadatas[i:end],
                    ids=ids[i:end]
                )
        return f"Indexed {len(documents)} files."

    def query(self, query_text, n_results=3):
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        return results

# Singleton instance
memory = MemoryManager()

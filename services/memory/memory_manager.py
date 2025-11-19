import os
import chromadb
from chromadb.utils import embedding_functions
import glob

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class MemoryManager:
    def __init__(self, persist_path=None):
        if persist_path is None:
            persist_path = os.path.join(BASE_DIR, "services", "memory", "db")
            
        os.makedirs(persist_path, exist_ok=True)
        
        self.client = chromadb.PersistentClient(path=persist_path)
        self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        self.collection = self.client.get_or_create_collection(
            name="codebase_knowledge",
            embedding_function=self.embedding_fn
        )

    def chunk_content(self, content, file_path):
        chunks = []
        lines = content.split('\n')
        
        if file_path.endswith('.py'):
            current_chunk = []
            for line in lines:
                if (line.startswith('def ') or line.startswith('class ') or line.startswith('@')) and len(current_chunk) > 0:
                    if len('\n'.join(current_chunk)) < 50:
                        current_chunk.append(line)
                    else:
                        chunks.append('\n'.join(current_chunk))
                        current_chunk = [line]
                else:
                    current_chunk.append(line)
                    
                if len(current_chunk) > 100:
                    chunks.append('\n'.join(current_chunk))
                    current_chunk = []
            
            if current_chunk:
                chunks.append('\n'.join(current_chunk))
        else:
            current_chunk = []
            for line in lines:
                current_chunk.append(line)
                if len(current_chunk) > 50:
                    chunks.append('\n'.join(current_chunk))
                    current_chunk = []
            if current_chunk:
                chunks.append('\n'.join(current_chunk))
                
        return [c for c in chunks if c.strip()]

    def index_codebase(self):
        root_dirs = [os.path.join(BASE_DIR, "backend"), os.path.join(BASE_DIR, "services")]
        documents = []
        metadatas = []
        ids = []
        
        for root_dir in root_dirs:
            files = glob.glob(os.path.join(root_dir, "**", "*.py"), recursive=True)
            files.extend(glob.glob(os.path.join(root_dir, "**", "*.txt"), recursive=True))
            files.extend(glob.glob(os.path.join(root_dir, "**", "*.md"), recursive=True))
            
            for file_path in files:
                if any(x in file_path for x in ["venv", "__pycache__", ".git", ".db", "node_modules"]):
                    continue
                    
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        if not content.strip():
                            continue
                            
                        file_chunks = self.chunk_content(content, file_path)
                        rel_path = os.path.relpath(file_path, BASE_DIR)
                        
                        for i, chunk in enumerate(file_chunks):
                            documents.append(chunk)
                            metadatas.append({"source": rel_path, "chunk_id": i})
                            ids.append(f"{rel_path}_{i}")
                except Exception as e:
                    print(f"Skipping {file_path}: {e}")

        if documents:
            batch_size = 100
            for i in range(0, len(documents), batch_size):
                end = min(i + batch_size, len(documents))
                self.collection.upsert(
                    documents=documents[i:end],
                    metadatas=metadatas[i:end],
                    ids=ids[i:end]
                )
        return f"Indexed {len(documents)} chunks from codebase."

    def index_text(self, source: str, text: str):
        """Indexes arbitrary text content (e.g., from documentation)."""
        chunks = self.chunk_content(text, source)
        documents = []
        metadatas = []
        ids = []
        
        # Sanitize source for ID
        safe_source = "".join([c if c.isalnum() else "_" for c in source])[-50:]
        
        for i, chunk in enumerate(chunks):
            documents.append(chunk)
            metadatas.append({"source": source, "chunk_id": i, "type": "external_knowledge"})
            ids.append(f"ext_{safe_source}_{i}")
            
        if documents:
            self.collection.upsert(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
        return f"Indexed {len(documents)} chunks from {source}."

    def query(self, query_text, n_results=3):
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        return results

memory = MemoryManager()

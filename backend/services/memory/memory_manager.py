"""Vector memory manager with ChromaDB."""

import os
import glob
import asyncio
from typing import Any
from backend.config import settings
from backend.logger import logger

try:
    import aiofiles
    AIOFILES = True
except ImportError:
    AIOFILES = False

try:
    import chromadb
    from chromadb.utils import embedding_functions
    CHROMA = True
except ImportError:
    CHROMA = False
    chromadb = None

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKIP_PATTERNS = ["venv", "__pycache__", ".git", ".db", "node_modules"]


class MemoryManager:
    """Vector memory for codebase knowledge."""
    
    def __init__(self, path: str | None = None):
        self.collection = None
        if not CHROMA:
            logger.warning("ChromaDB not installed")
            return
        
        path = path or settings.MEMORY_INDEX_PATH
        os.makedirs(path, exist_ok=True)
        
        self.client = chromadb.PersistentClient(path=path)
        self.collection = self.client.get_or_create_collection(
            name="codebase_knowledge",
            embedding_function=embedding_functions.DefaultEmbeddingFunction()
        )
        logger.info("💾 Memory loaded")
    
    async def index_codebase(self) -> str:
        """Index codebase files."""
        if not self.collection:
            return "Memory disabled"
        
        if not AIOFILES:
            return self._index_sync()
        
        docs, metas, ids = [], [], []
        
        for root in [os.path.join(BASE_DIR, "backend"), os.path.join(BASE_DIR, "services")]:
            if not os.path.exists(root):
                continue
            
            for ext in ("*.py", "*.txt", "*.md"):
                for path in glob.glob(os.path.join(root, "**", ext), recursive=True):
                    if any(p in path for p in SKIP_PATTERNS):
                        continue
                    
                    try:
                        async with aiofiles.open(path, "r", encoding="utf-8") as f:
                            content = await f.read()
                        if not content.strip():
                            continue
                        
                        rel = os.path.relpath(path, BASE_DIR)
                        for i, chunk in enumerate(self._chunk(content, path)):
                            docs.append(chunk)
                            metas.append({"source": rel, "chunk_id": i})
                            ids.append(f"{rel}_{i}")
                    except Exception:
                        pass
        
        await self._upsert_batched(docs, metas, ids)
        return f"Indexed {len(docs)} chunks"
    
    def _index_sync(self) -> str:
        """Sync fallback."""
        docs, metas, ids = [], [], []
        
        for path in glob.glob(os.path.join(BASE_DIR, "backend", "**", "*.py"), recursive=True):
            if any(p in path for p in SKIP_PATTERNS):
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    rel = os.path.relpath(path, BASE_DIR)
                    for i, chunk in enumerate(self._chunk(f.read(), path)):
                        docs.append(chunk)
                        metas.append({"source": rel, "chunk_id": i})
                        ids.append(f"{rel}_{i}")
            except Exception:
                pass
        
        if docs:
            self.collection.upsert(documents=docs, metadatas=metas, ids=ids)
        return f"Indexed {len(docs)} chunks"
    
    async def index_text(self, source: str, text: str) -> str:
        """Index external text."""
        if not self.collection:
            return "Memory disabled"
        
        safe = "".join(c if c.isalnum() else "_" for c in source)[-50:]
        docs, metas, ids = [], [], []
        
        for i, chunk in enumerate(self._chunk(text, source)):
            docs.append(chunk)
            metas.append({"source": source, "chunk_id": i, "type": "external"})
            ids.append(f"ext_{safe}_{i}")
        
        await self._upsert_batched(docs, metas, ids)
        return f"Indexed {len(docs)} chunks from {source}"
    
    async def query(self, text: str, n: int = 3) -> dict[str, Any]:
        """Query memory."""
        if not self.collection:
            return {"documents": [], "metadatas": []}
        
        return await asyncio.to_thread(
            self.collection.query, query_texts=[text], n_results=n
        )
    
    async def _upsert_batched(self, docs: list, metas: list, ids: list, batch: int = 100):
        """Upsert in batches to avoid blocking."""
        for i in range(0, len(docs), batch):
            end = min(i + batch, len(docs))
            await asyncio.to_thread(
                self.collection.upsert,
                documents=docs[i:end], metadatas=metas[i:end], ids=ids[i:end]
            )
    
    def _chunk(self, content: str, path: str) -> list[str]:
        """Split content into chunks."""
        lines = content.split('\n')
        chunks = []
        current = []
        
        is_python = path.endswith('.py')
        limit = 100 if is_python else 50
        
        for line in lines:
            if is_python and (line.startswith('def ') or line.startswith('class ')) and len(current) > 5:
                chunks.append('\n'.join(current))
                current = []
            
            current.append(line)
            if len(current) > limit:
                chunks.append('\n'.join(current))
                current = []
        
        if current:
            chunks.append('\n'.join(current))
        
        return [c for c in chunks if c.strip()]


memory = MemoryManager()

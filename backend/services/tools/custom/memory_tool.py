"""Memory query and indexing tools."""

from backend.services.memory.memory_manager import memory


async def query_memory(query: str) -> str:
    """Search codebase memory for relevant snippets."""
    try:
        results = await memory.query(query, n=3)
        
        if not results.get('documents') or not results['documents'][0]:
            return "No results found"
        
        output = []
        for i, doc in enumerate(results['documents'][0]):
            source = results['metadatas'][0][i].get('source', 'unknown')
            output.append(f"--- {source} ---\n{doc[:1000]}...")
        
        return "\n\n".join(output)
    except Exception as e:
        return f"Query error: {e}"


async def index_memory() -> str:
    """Re-index codebase for memory queries."""
    try:
        result = await memory.index_codebase()
        return f"Indexed: {result}"
    except Exception as e:
        return f"Index error: {e}"

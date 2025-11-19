from services.memory.memory_manager import memory

async def query_memory(query: str) -> str:
    """
    Searches the codebase memory for relevant code snippets or documentation.
    Useful for understanding how existing features are implemented before modifying them.
    """
    try:
        # Auto-index on first query if empty? Or just assume it's indexed.
        # Let's trigger a quick index refresh if it's a "how to" query to ensure freshness, 
        # but that might be slow. Let's assume it's indexed or index explicitly.
        # For this implementation, we'll just query.
        
        results = memory.query(query, n_results=3)
        
        output = []
        if results['documents']:
            for i, doc in enumerate(results['documents'][0]):
                source = results['metadatas'][0][i]['source']
                output.append(f"--- Source: {source} ---\n{doc[:1000]}...\n(truncated)\n")
        
        return "\n".join(output) if output else "No relevant information found in memory."
    except Exception as e:
        return f"Memory query error: {str(e)}"

async def index_memory() -> str:
    """
    Forces a re-indexing of the codebase. Use this after making significant changes.
    """
    try:
        res = memory.index_codebase()
        return f"Memory re-indexed: {res}"
    except Exception as e:
        return f"Indexing error: {str(e)}"

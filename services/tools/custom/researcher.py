import aiohttp
from bs4 import BeautifulSoup
from ...memory.memory_manager import memory
import urllib.parse

async def learn_tech(topic: str, url: str = None) -> str:
    """
    Learns about a new technology or library by reading documentation.
    If URL is provided, it scrapes it. If not, it asks for one (or could search if implemented).
    Indexes the learned content into the vector memory.
    """
    if not url:
        return f"Please provide a specific URL to the documentation for '{topic}'. I need a source to learn from."

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=30) as response:
                if response.status != 200:
                    return f"Error fetching URL {url}: Status {response.status}"
                html = await response.text()
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "iframe", "noscript"]):
            script.decompose()
            
        # Get text
        text = soup.get_text(separator='\n')
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        clean_text = '\n'.join(chunk for chunk in chunks if chunk)
        
        if not clean_text:
            return "Error: No text content found at URL."

        # Index into memory
        # We use the topic as part of the source to make it easily searchable
        source_id = f"doc_{topic}_{urllib.parse.quote(url, safe='')}"
        result = memory.index_text(source=source_id, text=clean_text)
        
        summary = clean_text[:500] + "..." if len(clean_text) > 500 else clean_text
        return f"Successfully learned about '{topic}' from {url}.\n{result}\n\nContent Preview:\n{summary}"
        
    except Exception as e:
        return f"Error learning technology: {str(e)}"


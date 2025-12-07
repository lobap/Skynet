"""Technology documentation research and learning tool."""

import urllib.parse
from backend.services.memory.memory_manager import memory

try:
    import aiohttp
    from bs4 import BeautifulSoup
    DEPS_AVAILABLE = True
except ImportError:
    DEPS_AVAILABLE = False
    aiohttp = None
    BeautifulSoup = None


async def learn_tech(topic: str, url: str | None = None) -> str:
    """Learn about technology by reading documentation.
    
    Args:
        topic: Technology/library name
        url: Documentation URL to scrape
    """
    if not DEPS_AVAILABLE:
        return "Missing: aiohttp, beautifulsoup4"
    
    if not url:
        return f"Provide URL for '{topic}' documentation"
    
    try:
        text = await _fetch_and_parse(url)
        if not text:
            return "No text content found"
        
        source_id = f"doc_{topic}_{urllib.parse.quote(url, safe='')}"
        result = await memory.index_text(source=source_id, text=text)
        
        preview = text[:500] + "..." if len(text) > 500 else text
        return f"Learned '{topic}' from {url}\n{result}\n\nPreview:\n{preview}"
        
    except Exception as e:
        return f"Error: {e}"


async def _fetch_and_parse(url: str) -> str:
    """Fetch URL and extract text content."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=30) as response:
            if response.status != 200:
                raise Exception(f"HTTP {response.status}")
            html = await response.text()
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # Remove non-content elements
    for tag in soup(["script", "style", "nav", "footer", "iframe", "noscript"]):
        tag.decompose()
    
    text = soup.get_text(separator='\n')
    
    # Clean whitespace
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    return '\n'.join(chunk for chunk in chunks if chunk)

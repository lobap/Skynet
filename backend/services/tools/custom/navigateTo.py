async def navigateTo(url: str) -> str:
    """
    Navigate to a specified URL and return the content of the page as a string.
    
    Args:
        url (str): The URL to navigate to.
        
    Returns:
        str: The content of the page at the specified URL.
    """
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()
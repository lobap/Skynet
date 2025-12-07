"""Simple URL navigation tool."""

import aiohttp


async def navigateTo(url: str) -> str:
    """Fetch URL content."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()
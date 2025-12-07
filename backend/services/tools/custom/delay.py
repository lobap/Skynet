"""Simple delay tool."""

import asyncio


async def delay(seconds: int = 60) -> str:
    """Pause execution for N seconds."""
    await asyncio.sleep(seconds)
    return f"Waited {seconds}s"
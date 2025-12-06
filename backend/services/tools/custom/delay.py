import asyncio

async def delay(seconds: int = 60) -> None:
    """
    Pauses the execution of the coroutine for a specified number of seconds.

    Parameters:
    seconds (int): The number of seconds to pause. Defaults to 60.
    """
    await asyncio.sleep(seconds)
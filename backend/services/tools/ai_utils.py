"""AI utility for consulting LLM models."""

import asyncio
import ollama
from backend.config import settings
from backend.logger import logger

HOST = settings.OLLAMA_HOST
VALID_MODELS = {settings.MODEL_FAST, settings.MODEL_REASONING, settings.MODEL_CODING}
MAX_RETRIES = 3
TIMEOUT = 120


async def consult_ai(model: str, system_prompt: str, user_input: str, json_mode: bool = False) -> str:
    """Centralized AI consultation with retry logic.
    
    Args:
        model: Model identifier
        system_prompt: System instruction
        user_input: User query
        json_mode: If True, enforce JSON output
    """
    if model not in VALID_MODELS:
        logger.warning(f"Invalid model '{model}', using {settings.MODEL_FAST}")
        model = settings.MODEL_FAST
    
    client = ollama.AsyncClient(host=HOST)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input}
    ]
    
    for attempt in range(MAX_RETRIES):
        try:
            response = await asyncio.wait_for(
                client.chat(
                    model=model,
                    messages=messages,
                    format="json" if json_mode else None
                ),
                timeout=TIMEOUT
            )
            return response['message']['content']
        except asyncio.TimeoutError:
            logger.warning(f"Timeout ({attempt + 1}/{MAX_RETRIES})")
            if attempt == MAX_RETRIES - 1:
                return f"Error: {model} timed out"
        except Exception as e:
            logger.error(f"AI error ({attempt + 1}): {e}")
            if attempt == MAX_RETRIES - 1:
                return f"Error: {e}"
            await asyncio.sleep(attempt + 1)
    
    return "Error: AI consultation failed"

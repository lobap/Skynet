import ollama
import asyncio
from backend.config import settings
from backend.logger import logger

HOST = settings.OLLAMA_HOST
VALID_MODELS = [settings.MODEL_FAST, settings.MODEL_REASONING, settings.MODEL_CODING]

async def consult_ai(model: str, system_prompt: str, user_input: str, json_mode: bool = False) -> str:
    """
    Centralized AI access point.
    
    Args:
        model (str): The model identifier (e.g., 'qwen2.5-coder:1.5b').
        system_prompt (str): The system instruction.
        user_input (str): The user's query or context.
        json_mode (bool): If True, enforces JSON output format.
        
    Returns:
        str: The model's response content.
    """
    # Validate model name - fallback to MODEL_FAST if invalid
    if model not in VALID_MODELS:
        logger.warning(f"Invalid model '{model}' specified. Using fallback: {settings.MODEL_FAST}")
        model = settings.MODEL_FAST
    
    client = ollama.AsyncClient(host=HOST)
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input}
    ]
    
    options = {}
    format_param = "json" if json_mode else None
    
    # Retry logic for robustness
    max_retries = 3
    for attempt in range(max_retries):
        try:
            logger.debug(f"Sending request to {model}...")
            response = await asyncio.wait_for(
                client.chat(
                    model=model,
                    messages=messages,
                    format=format_param,
                    options=options
                ),
                timeout=120.0
            )
            logger.debug(f"Response received ({len(response['message']['content'])} chars).")
            return response['message']['content']
        except asyncio.TimeoutError:
            logger.warning(f"AI Timeout Error (Attempt {attempt+1}/{max_retries})")
            if attempt == max_retries - 1:
                return f"Error: AI Model ({model}) timed out after 120 seconds."
        except Exception as e:
            logger.error(f"AI Consultation Error (Attempt {attempt+1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                return f"Error communicating with AI model {model}: {str(e)}"
            await asyncio.sleep(1 * (attempt + 1))
            
    return "Error: AI consultation failed."

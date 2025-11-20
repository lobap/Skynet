import ollama
import os
import asyncio
from dotenv import load_dotenv

# Load env from backend
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'backend', '.env'))

HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")

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
            print(f"⏳ [AI] Enviando petición a {model}...")
            response = await asyncio.wait_for(
                client.chat(
                    model=model,
                    messages=messages,
                    format=format_param,
                    options=options
                ),
                timeout=120.0
            )
            print(f"✅ [AI] Respuesta recibida ({len(response['message']['content'])} chars).")
            return response['message']['content']
        except asyncio.TimeoutError:
            print(f"AI Timeout Error (Attempt {attempt+1}/{max_retries})")
            if attempt == max_retries - 1:
                return f"Error: AI Model ({model}) timed out after 120 seconds."
        except Exception as e:
            print(f"AI Consultation Error (Attempt {attempt+1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                return f"Error communicating with AI model {model}: {str(e)}"
            await asyncio.sleep(1 * (attempt + 1)) # Exponential backoff
            
    return "Error: AI consultation failed."

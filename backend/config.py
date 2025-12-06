import os
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List

class Settings(BaseSettings):
    # Project Info
    PROJECT_NAME: str = "Skynet"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    
    # AI Models
    MODEL_FAST: str = "qwen2.5-coder:7b"
    MODEL_REASONING: str = "qwen2.5-coder:7b"
    MODEL_CODING: str = "qwen2.5-coder:7b"
    OLLAMA_HOST: str = "http://127.0.0.1:11434"
    
    # Agent Behavior
    MAX_AGENT_STEPS: int = 15
    MAX_CONSECUTIVE_FAILURES: int = 3
    MAX_CONSECUTIVE_LOOPS: int = 2
    MAX_TOTAL_FAILURES: int = 10
    SIGNATURE_HISTORY_SIZE: int = 6
    
    # Shell Security
    SHELL_BLOCKED_PATTERNS: List[str] = [
        "rm -rf /", "rm -rf ~", "rm -rf .", "chmod 777",
        ":(){ :|:& };:", "> /dev/sda", "mkfs.", "dd if=",
        "sudo rm", "sudo chmod", "format c:", "del /f /s /q"
    ]
    
    # Paths
    DATABASE_URL: str = "sqlite:///./backend/services/database/agente.db"
    MEMORY_INDEX_PATH: str = "./backend/services/memory/chroma_data"
    GENERATED_SCRIPTS_PATH: str = "./scripts/generated"
    CUSTOM_TOOLS_PATH: str = "./backend/services/tools/custom"
    
    # Credentials
    SUDO_PASSWORD: str = ""
    TELEGRAM_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()

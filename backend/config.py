import os
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    PROJECT_NAME: str = "Skynet"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    
    MODEL_FAST: str = "qwen2.5-coder:1.5b"
    MODEL_REASONING: str = "qwen2.5-coder:1.5b"
    MODEL_CODING: str = "qwen2.5-coder:1.5b"
    OLLAMA_HOST: str = "http://127.0.0.1:11434"
    MAX_AGENT_STEPS: int = 10
    
    DATABASE_URL: str = "sqlite:///./services/database/agente.db"
    
    SUDO_PASSWORD: str = ""
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()

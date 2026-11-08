from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    repo_root: Path = Path('/workspace')
    index_dir: Path = Path('/app/data')
    site_base_url: str = 'https://iand4096.github.io/docusaurusportfolio/'
    cors_origins: str = 'http://localhost:3000,http://localhost:3001'
    embedding_model: str = 'sentence-transformers/all-MiniLM-L6-v2'
    deepseek_api_key: str = ''
    deepseek_base_url: str = 'https://api.deepseek.com'
    deepseek_model: str = 'deepseek-chat'

@lru_cache

def get_settings() -> Settings:
    return Settings()

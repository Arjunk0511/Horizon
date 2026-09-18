from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
ROOT = Path(__file__).resolve().parents[2]
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT/'backend'/'.env', extra='ignore')
    database_url: str = 'sqlite:///' + str(ROOT/'backend'/'horizon.db')
    jwt_secret_key: str = ''
    demo_mode: bool = True
    demo_password: str = ''
    weather_api_key: str = ''
    ais_api_key: str = ''
    ais_url: str = ''
    cors_origins: list[str] = ['http://localhost:5173','http://127.0.0.1:5173']
settings = Settings()

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")
    database_url: str = (
        "postgresql+psycopg://researchdesk:researchdesk@127.0.0.1:55432/researchdesk"
    )
    sec_user_agent: str = ""
    llm_backend: str = "mlx"
    llm_model: str = "mlx-community/Qwen3-4B-Instruct-2507-4bit"
    local_llm_url: str = "http://127.0.0.1:8081/v1/chat/completions"
    llm_timeout: int = Field(default=90, ge=1, le=90)
    llm_max_tokens: int = Field(default=650, ge=1, le=650)
    data_dir: Path = ROOT / "data"


settings = Settings()

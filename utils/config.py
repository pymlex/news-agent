from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment and optional .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    zvenoai_api_key: str = ""
    zvenoai_base_url: str = "https://api.zveno.ai/v1"
    zvenoai_model: str = "qwen/qwen3.7-flash"
    database_path: str = "data/news_agent.sqlite3"
    max_search_results: int = 20
    max_search_hard_cap: int = 30
    gradio_server_name: str = "127.0.0.1"
    gradio_server_port: int = 7860


    def ensure_data_dir(self) -> Path:
        """Create the database parent directory when missing."""

        path = Path(self.database_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()

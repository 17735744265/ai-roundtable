"""Application configuration loaded from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    APP_NAME: str = "AI Roundtable"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite+aiosqlite:///./data/roundtable.db",
    )

    # LLM Provider: "deepseek" | "anthropic" | "openai"
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "deepseek")

    # DeepSeek (primary, via langchain-openai ChatOpenAI)
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL: str = os.getenv(
        "DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"
    )
    DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    # Anthropic (fallback)
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_BASE_URL: str = os.getenv(
        "ANTHROPIC_BASE_URL", "https://api.anthropic.com"
    )
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

    # OpenAI (fallback)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # Discussion config
    FREE_DISCUSSION_ROUNDS: int = int(os.getenv("FREE_DISCUSSION_ROUNDS", "30"))

    # CORS
    CORS_ORIGINS: list[str] = os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"
    ).split(",")

    @property
    def deepseek_available(self) -> bool:
        return bool(self.DEEPSEEK_API_KEY)

    @property
    def anthropic_available(self) -> bool:
        return bool(self.ANTHROPIC_API_KEY)

    @property
    def openai_available(self) -> bool:
        return bool(self.OPENAI_API_KEY)


settings = Settings()

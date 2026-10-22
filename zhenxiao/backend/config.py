from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / "model" / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM（OpenAI 兼容协议）
    dashscope_base_url: str = ""
    dashscope_chat_model: str = ""
    dashscope_embedding_model: str = ""
    dashscope_rerank_model: str = ""
    dashscope_rerank_url: str = ""
    dashscope_api_key_2: str = ""
    tavily_api_key: str = ""

    # 检索规模（规格书 3.9 / 4.2 /api/settings 输出 rag_top_k）
    rag_top_k: int = 6
    deep_search_enabled: bool = True

    # 数据库
    database_url: str = ""
    mysql_host: str = ""
    mysql_port: int = 3306
    mysql_user: str = ""
    mysql_password: str = ""
    mysql_database: str = ""

    @property
    def db_url(self) -> str:
        if self.database_url:
            return self.database_url
        if self.mysql_host:
            return (
                f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
                f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
            )
        return f"sqlite:///{(BASE_DIR / 'zhenxiao.db').as_posix()}"


settings = Settings()

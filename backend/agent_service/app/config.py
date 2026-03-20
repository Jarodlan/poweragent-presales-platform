from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "dev"
    app_port: int = 9000
    qwen_api_key: str = ""
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    qwen_default_model: str = "qwen3.5-plus"
    qwen_review_model: str = "qwen-max-latest"
    minimax_api_key: str = ""
    minimax_base_url: str = "https://api.minimaxi.com/v1"
    minimax_default_model: str = "MiniMax-M2.7"
    minimax_fast_model: str = "MiniMax-M2.7-highspeed"
    ragflow_base_url: str = "http://127.0.0.1:9380"
    ragflow_api_key: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

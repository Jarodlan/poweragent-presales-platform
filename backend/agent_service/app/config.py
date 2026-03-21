import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    repo_root: Path = Path(__file__).resolve().parents[3]
    app_env: str = "dev"
    app_port: int = 9000
    llm_http_timeout_sec: int = 300
    qwen_api_key: str = os.getenv("QWEN_API_KEY") or os.getenv("DASHSCOPE_API_KEY") or ""
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    qwen_default_model: str = "qwen3-max"
    qwen_review_model: str = "qwen3-max"
    minimax_api_key: str = ""
    minimax_base_url: str = "https://api.minimaxi.com/v1"
    minimax_default_model: str = "MiniMax-M2.5"
    minimax_fast_model: str = "MiniMax-M2.5-highspeed"
    ragflow_base_url: str = "http://127.0.0.1:9380"
    ragflow_api_key: str = ""
    ragflow_dataset_papers: str = ""
    ragflow_dataset_standards: str = ""
    ragflow_dataset_cases: str = ""
    ragflow_dataset_solutions: str = ""
    solution_template_enabled: bool = True
    solution_template_path: str = str(Path(__file__).resolve().parents[3] / "智能电网故障诊断解决方案模板.md")
    solution_template_source_path: str = str(Path(__file__).resolve().parents[3] / "参考解决方案模板的内容.md")
    storage_solution_template_path: str = str(
        Path(__file__).resolve().parents[3] / "分布式储能聚合运营智能体解决方案模板.md"
    )
    storage_solution_template_source_path: str = str(
        Path(__file__).resolve().parents[3] / "分布式储能聚合运营智能体解决方案模板.md"
    )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

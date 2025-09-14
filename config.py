from typing import Optional, List, Literal, Dict
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """集中化配置，支持从环境变量与 .env 加载。

    关键环境变量：
    - DASHSCOPE_API_KEY: 通义千问 API Key
    - SSL_CERTFILE / SSL_KEYFILE: TLS 证书/私钥文件路径
    - SSL_KEYFILE_PASSWORD: 私钥密码（如有）
    """

    # 应用与服务
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)

    # LLM 设置
    model_name: str = Field(default="qwen-turbo")
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)

    # 会话/历史
    history_limit: int = Field(default=10, ge=1)

    # 模型key
    dashscope_api_key: str = Field(default="")

    # TLS/SSL
    ssl_certfile: Optional[str] = None
    ssl_keyfile: Optional[str] = None
    ssl_keyfile_password: Optional[str] = None

    # CORS（开发联调用），留空则不启用
    allowed_origins: List[str] = Field(default_factory=list)
    allowed_methods: List[str] = Field(default_factory=lambda: ["GET", "POST", "OPTIONS"]) 

    # 鉴权
    require_api_key: bool = Field(default=False)
    internal_api_key: Optional[str] = None  # 从环境变量 INTERNAL_API_KEY 读取（若启用鉴权）
    internal_api_keys: List[str] = Field(default_factory=list)  # 可选：多密钥支持（JSON 数组或逗号分隔需按 JSON）
    api_keys: Dict[str, str] = Field(default_factory=dict)  # KID->KEY（JSON 对象）

    # 速率限制（内存级，轻量）
    rate_limit_enabled: bool = Field(default=False)
    rate_limit_requests: int = Field(default=60, ge=1)  # 窗口内允许的最大请求数
    rate_limit_window_s: int = Field(default=60, ge=1)  # 窗口大小（秒）
    rate_limit_by: Literal["ip", "api_key"] = Field(default="ip")

    # 请求体大小限制（字节）
    request_max_body_bytes: int = Field(default=1_000_000, ge=1)  # 约 1MB

    # 日志与脱敏
    log_level: str = Field(default="INFO")
    log_truncate_len: int = Field(default=1000, ge=100)

    # 短期签名 URL（用于 GET /chat/stream）
    signed_url_enabled: bool = Field(default=True)
    signed_url_ttl_s: int = Field(default=300, ge=30)
    signed_url_clock_skew_s: int = Field(default=30, ge=0)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

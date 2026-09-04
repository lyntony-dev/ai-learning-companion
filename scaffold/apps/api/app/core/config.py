from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# dev 占位默认值:APP_ENV=production 时若仍是这些值则启动失败(fail-fast)
DEV_TOKEN_SECRET = "dev-insecure-secret-change-me"
DEV_TEACHER_INVITE = "dev-teacher-invite"


class ConfigError(RuntimeError):
    """生产配置校验失败(如密钥仍是 dev 占位)。"""


class Settings(BaseSettings):
    """Runtime configuration for the API service."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="local", alias="APP_ENV")
    app_log_level: str = Field(default="INFO", alias="APP_LOG_LEVEL")
    database_url: str = Field(default="sqlite:///data/app.sqlite", alias="DATABASE_URL")
    # 引擎业务库(SQLModel, ADR-0005),与脚手架 RAG/对话库 database_url 物理分离
    business_db_url: str = Field(
        default="sqlite:///data/business.sqlite", alias="BUSINESS_DB_URL"
    )
    chroma_persist_dir: str = Field(default="data/chroma", alias="CHROMA_PERSIST_DIR")
    course_materials_dir: str = Field(default="data/course_materials", alias="COURSE_MATERIALS_DIR")

    # --- LLM (Ark VLM，走标准 /chat/completions；见 ADR-0003) ---
    llm_provider: str = Field(default="mock", alias="LLM_PROVIDER")
    llm_base_url: str = Field(default="", alias="LLM_BASE_URL")
    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    llm_model: str = Field(default="", alias="LLM_MODEL")
    llm_timeout_seconds: int = Field(default=30, alias="LLM_TIMEOUT_SECONDS")
    llm_max_tokens: int = Field(default=2048, alias="LLM_MAX_TOKENS")
    llm_temperature: float = Field(default=0.2, alias="LLM_TEMPERATURE")

    # --- Embedding (Ark 多模态，走 /embeddings/multimodal；见 ADR-0003) ---
    # provider 三选一:ark_multimodal(真实 Ark)/ local(本地离线向量模型,无需 key)/ mock(默认)
    embedding_provider: str = Field(default="mock", alias="EMBEDDING_PROVIDER")
    embedding_base_url: str = Field(default="", alias="EMBEDDING_BASE_URL")
    embedding_api_key: str = Field(default="", alias="EMBEDDING_API_KEY")
    embedding_model: str = Field(default="", alias="EMBEDDING_MODEL")
    embedding_dim: int = Field(default=768, alias="EMBEDDING_DIM")
    embedding_batch_size: int = Field(default=16, alias="EMBEDDING_BATCH_SIZE")
    # local provider 用的 sentence-transformers 模型名(中文语义检索,~95MB,首次用时自动下载)
    local_embedding_model: str = Field(
        default="BAAI/bge-small-zh-v1.5", alias="LOCAL_EMBEDDING_MODEL"
    )

    default_user_id: str = Field(default="demo_user", alias="DEFAULT_USER_ID")
    trace_debug_full: bool = Field(default=False, alias="TRACE_DEBUG_FULL")
    max_retrieval_retry: int = Field(default=1, alias="MAX_RETRIEVAL_RETRY")
    max_generate_retry: int = Field(default=1, alias="MAX_GENERATE_RETRY")

    # --- 学生登录/身份(ADR-0008)。轻量签名 token,非 JWT 库,dev 默认密钥可用 ---
    auth_token_secret: str = Field(
        default=DEV_TOKEN_SECRET, alias="AUTH_TOKEN_SECRET"
    )
    auth_token_ttl_hours: int = Field(default=168, alias="AUTH_TOKEN_TTL_HOURS")
    # 讲师注册邀请码(讲师账号非自由注册;dev 占位,生产必须覆盖,同 AUTH_TOKEN_SECRET)
    auth_teacher_invite_code: str = Field(
        default=DEV_TEACHER_INVITE, alias="AUTH_TEACHER_INVITE_CODE"
    )

    app_name: str = "ai-agent-course-tutor-api"
    app_version: str = "0.2.0"

    # --- CORS(生产前后端分离部署用;默认空=关闭,因默认部署走 nginx 同源反代)---
    # 逗号分隔的允许来源,如 "https://tutor.example.com,https://staging.example.com"
    cors_allow_origins: str = Field(default="", alias="CORS_ALLOW_ORIGINS")

    @property
    def cors_origins_list(self) -> list[str]:
        """把逗号分隔的 CORS_ALLOW_ORIGINS 解析为去空白的来源列表(空则返回空列表)。"""

        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"production", "prod"}

    def validate_production(self) -> None:
        """生产环境启动前的 fail-fast 校验:dev 占位密钥必须被覆盖。

        APP_ENV=production 时,若安全敏感项仍是 dev 默认值,直接抛错拒绝启动,
        避免带着可预测密钥上线(见 ADR-0008/0009)。
        """

        if not self.is_production:
            return
        insecure: list[str] = []
        if self.auth_token_secret == DEV_TOKEN_SECRET:
            insecure.append("AUTH_TOKEN_SECRET")
        if self.auth_teacher_invite_code == DEV_TEACHER_INVITE:
            insecure.append("AUTH_TEACHER_INVITE_CODE")
        if insecure:
            raise ConfigError(
                "APP_ENV=production 但以下密钥仍是 dev 默认值,拒绝启动: "
                + ", ".join(insecure)
                + "。请在部署环境覆盖它们。"
            )


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()

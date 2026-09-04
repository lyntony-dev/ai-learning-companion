"""feat-001 基线:确认 .env 的 Ark 配置能被 Settings 载入。

对齐 docs/adr/0003-ark-multimodal-embedding.md 与 docs/DESIGN.md §7。
测试从 repo 根目录读取 .env(config.py 用相对路径 env_file=".env")。
在缺少 .env 的环境(如 CI)下自动跳过,不阻塞其它测试。
"""

from pathlib import Path

import pytest

from app.core.config import Settings

REPO_ROOT = Path(__file__).resolve().parents[4]
ENV_FILE = REPO_ROOT / ".env"


@pytest.mark.skipif(not ENV_FILE.exists(), reason="本地 .env 不存在(CI 环境),跳过真实配置载入校验")
def test_env_loads_real_provider_config() -> None:
    """本地 .env 能被完整载入,且真实 provider 的必填项齐全。

    这里断言的是「配置装配正确」,不是「必须用某一家」:provider 可在
    Ark / DeepSeek 等 OpenAI 兼容服务之间切换,换一家不应让测试变红。
    """
    settings = Settings(_env_file=str(ENV_FILE))

    # LLM 走标准 /chat/completions
    assert settings.llm_provider in {"openai_compatible", "mock"}
    if settings.llm_provider != "mock":
        assert settings.llm_base_url.startswith("http")
        assert settings.llm_model
        assert settings.llm_api_key  # 已注入,不断言明文

    # Embedding:local / mock 自带模型,只有远程 provider 需要 endpoint 与 key
    assert settings.embedding_provider in {"ark_multimodal", "local", "mock"}
    assert settings.embedding_dim > 0
    if settings.embedding_provider == "ark_multimodal":
        assert settings.embedding_model
        assert settings.embedding_api_key


def test_settings_defaults_without_env() -> None:
    """无 .env 时 mock 默认值成立,保证离线可跑。"""
    settings = Settings(_env_file=None)
    assert settings.llm_provider == "mock"
    assert settings.embedding_provider == "mock"
    assert settings.app_version == "0.2.0"


def test_validate_production_blocks_dev_secrets() -> None:
    """APP_ENV=production 但密钥仍是 dev 占位时,拒绝启动(fail-fast)。"""
    from app.core.config import ConfigError

    settings = Settings(_env_file=None, APP_ENV="production")
    with pytest.raises(ConfigError) as exc:
        settings.validate_production()
    assert "AUTH_TOKEN_SECRET" in str(exc.value)
    assert "AUTH_TEACHER_INVITE_CODE" in str(exc.value)


def test_validate_production_passes_with_overrides() -> None:
    """密钥被覆盖后生产校验通过;非生产环境不校验。"""
    ok = Settings(
        _env_file=None,
        APP_ENV="production",
        AUTH_TOKEN_SECRET="a-real-long-secret",
        AUTH_TEACHER_INVITE_CODE="a-real-invite",
    )
    ok.validate_production()  # 不抛错
    assert ok.is_production is True

    local = Settings(_env_file=None)  # 默认 APP_ENV=local
    local.validate_production()  # dev 占位在非生产环境不拦截
    assert local.is_production is False


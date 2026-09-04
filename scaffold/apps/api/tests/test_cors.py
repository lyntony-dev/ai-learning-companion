"""Tier 1-2:CORS 仅在显式配置 CORS_ALLOW_ORIGINS 时启用(ADR-0010)。

默认部署走 nginx 同源反代,不加 CORS 头;前后端分离部署时按逗号分隔来源开启。
"""

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings


def _client_with_cors(monkeypatch, value: str | None) -> TestClient:
    if value is None:
        monkeypatch.delenv("CORS_ALLOW_ORIGINS", raising=False)
    else:
        monkeypatch.setenv("CORS_ALLOW_ORIGINS", value)
    get_settings.cache_clear()
    # 延迟导入并重建 app,确保读到当前环境
    from app.main import create_app

    return TestClient(create_app())


def test_cors_origins_parsing() -> None:
    s = Settings(_env_file=None, CORS_ALLOW_ORIGINS=" https://a.com , https://b.com ,")
    assert s.cors_origins_list == ["https://a.com", "https://b.com"]

    empty = Settings(_env_file=None)
    assert empty.cors_origins_list == []


def test_cors_disabled_by_default(monkeypatch) -> None:
    client = _client_with_cors(monkeypatch, None)
    resp = client.get("/healthz", headers={"Origin": "https://tutor.example.com"})
    assert resp.status_code == 200
    assert "access-control-allow-origin" not in {k.lower() for k in resp.headers}
    get_settings.cache_clear()


def test_cors_enabled_for_configured_origin(monkeypatch) -> None:
    client = _client_with_cors(monkeypatch, "https://tutor.example.com")
    resp = client.get("/healthz", headers={"Origin": "https://tutor.example.com"})
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "https://tutor.example.com"
    get_settings.cache_clear()

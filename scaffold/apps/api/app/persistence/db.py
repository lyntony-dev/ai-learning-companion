"""引擎业务库的 engine / session 管理 (ADR-0005 / DESIGN §5)。

走 BUSINESS_DB_URL,与脚手架的 database_url(RAG/对话库)物理分离。
建表用 SQLModel.metadata;领域表全部通过 import models 注册到 metadata。
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import Settings, get_settings
from app.db.sqlite import ensure_parent_dir, resolve_sqlite_path

# 确保所有领域表在 import 时注册进 SQLModel.metadata
from app.persistence import models as _models  # noqa: F401

_engine: Engine | None = None


def get_engine(settings: Settings | None = None) -> Engine:
    """返回业务库 engine(单例)。SQLite 需 check_same_thread=False 以配合 FastAPI。"""

    global _engine
    if _engine is not None:
        return _engine

    settings = settings or get_settings()
    database_path = resolve_sqlite_path(settings.business_db_url)
    ensure_parent_dir(database_path)

    _engine = create_engine(
        settings.business_db_url,
        connect_args={"check_same_thread": False},
    )
    return _engine


def init_business_db(settings: Settings | None = None) -> Engine:
    """建表(幂等)。返回 engine。"""

    engine = get_engine(settings)
    SQLModel.metadata.create_all(engine)
    return engine


@contextmanager
def get_session(settings: Settings | None = None) -> Iterator[Session]:
    """业务库会话上下文,提交/回滚由调用方语义驱动。"""

    engine = get_engine(settings)
    with Session(engine) as session:
        yield session


def reset_engine() -> None:
    """测试辅助:清空单例,便于用不同 DB URL 重建。"""

    global _engine
    if _engine is not None:
        _engine.dispose()
    _engine = None

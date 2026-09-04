from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import configure_logging, request_logging_middleware
from app.routes.admin import router as admin_router
from app.routes.archive import router as archive_router
from app.routes.auth import router as auth_router
from app.routes.capstone import router as capstone_router
from app.routes.chat import router as chat_router
from app.routes.courses import router as courses_router
from app.routes.health import router as health_router
from app.routes.insights import router as insights_router
from app.routes.training import router as training_router
from app.routes.version import router as version_router


def create_app() -> FastAPI:
    settings = get_settings()
    # 生产用 JSON 结构化日志(便于采集),本地用人类可读文本
    configure_logging(settings.app_log_level, json_format=settings.is_production)
    # 生产 fail-fast:APP_ENV=production 时 dev 占位密钥必须被覆盖(ADR-0008/0009)
    settings.validate_production()

    app = FastAPI(title=settings.app_name, version=settings.app_version)
    # CORS 仅在显式配置 CORS_ALLOW_ORIGINS 时启用(前后端分离部署);
    # 默认部署走 nginx 同源反代,无需 CORS。见 ADR-0010。
    if settings.cors_origins_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins_list,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["x-request-id"],
        )
    app.middleware("http")(request_logging_middleware)
    app.include_router(health_router)
    app.include_router(version_router)
    app.include_router(admin_router)
    app.include_router(auth_router)
    app.include_router(chat_router)
    app.include_router(courses_router)
    app.include_router(insights_router)
    app.include_router(training_router)
    app.include_router(capstone_router)
    app.include_router(archive_router)
    return app


app = create_app()

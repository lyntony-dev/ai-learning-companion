from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.schemas.common import VersionResponse

router = APIRouter(prefix="/api", tags=["version"])


@router.get("/version", response_model=VersionResponse)
def version(settings: Settings = Depends(get_settings)) -> VersionResponse:
    return VersionResponse(
        name=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
    )

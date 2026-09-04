from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.db.migrations import apply_migrations
from app.db.sqlite import connect
from app.schemas.common import DatabaseInitResponse

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/db/init", response_model=DatabaseInitResponse)
def init_database(settings: Settings = Depends(get_settings)) -> DatabaseInitResponse:
    """Apply pending SQLite migrations.

    This endpoint is a PR 2 local/admin skeleton and should be protected before any
    non-local deployment.
    """

    with connect(settings) as connection:
        applied = apply_migrations(connection)

    return DatabaseInitResponse(status="ok", applied_migrations=applied)

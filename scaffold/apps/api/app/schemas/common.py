from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class VersionResponse(BaseModel):
    name: str
    version: str
    environment: str


class DatabaseInitResponse(BaseModel):
    status: str
    applied_migrations: list[str]

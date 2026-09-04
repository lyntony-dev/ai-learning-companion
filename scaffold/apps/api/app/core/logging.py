import json
import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response

LOGGER_NAME = "course_tutor_api"


class JsonLogFormatter(logging.Formatter):
    """把日志行序列化为单行 JSON,便于生产环境日志采集/检索。

    额外字段(如 request_id/method/path)通过 logger.info(..., extra={...}) 注入,
    经 record.__dict__ 挑拣进 JSON。
    """

    _RESERVED = set(
        vars(logging.makeLogRecord({})).keys()
    ) | {"message", "asctime", "taskName"}

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in self._RESERVED and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str = "INFO", json_format: bool = False) -> None:
    """配置根日志。生产用 JSON 结构化输出,本地用人类可读文本。"""

    handler = logging.StreamHandler()
    if json_format:
        handler.setFormatter(JsonLogFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        )

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))


async def request_logging_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Attach request id and log safe request metadata."""

    logger = logging.getLogger(LOGGER_NAME)
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    started_at = time.perf_counter()

    response = await call_next(request)

    latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
    response.headers["x-request-id"] = request_id
    logger.info(
        "request_completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "latency_ms": latency_ms,
        },
    )
    return response

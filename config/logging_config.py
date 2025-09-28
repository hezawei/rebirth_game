"""
结构化日志记录配置
使用loguru提供强大的日志功能
"""

import sys
import uuid
from typing import Any

from loguru import logger


DEFAULT_EXTRA = {
    "trace": "-",
    "user": "-",
    "session": "-",
    "node": "-",
    "wish": "-",
    "task": "-",
}


def _format_console(record):
    extra = record.get("extra", {})
    ctx_parts = []
    for key in ("trace", "user", "session", "node", "task", "wish"):
        value = extra.get(key, "-")
        if value and value != "-":
            ctx_parts.append(f"{key}={value}")
    ctx_segment = (" ".join(ctx_parts) + " | ") if ctx_parts else ""
    return (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        f"{ctx_segment}"
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )


def _format_file(record):
    extra = record.get("extra", {})
    ctx_parts = []
    for key in ("trace", "user", "session", "node", "task", "wish"):
        value = extra.get(key, "-")
        if value and value != "-":
            ctx_parts.append(f"{key}={value}")
    ctx_segment = (" ".join(ctx_parts) + " | ") if ctx_parts else ""
    return (
        "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
        f"{ctx_segment}"
        "{name}:{function}:{line} - {message}\n"
    )


def setup_logger():
    """设定一个全局的日志记录器"""
    logger.remove()
    logger.configure(extra=dict(DEFAULT_EXTRA))

    logger.add(
        sys.stdout,
        level="INFO",
        format=_format_console,
    )

    logger.add(
        "rebirth_game.log",
        level="DEBUG",
        rotation="10 MB",
        retention="7 days",
        encoding="utf-8",
        format=_format_file,
    )

    return logger


def make_trace_id() -> str:
    return uuid.uuid4().hex[:8]


def _prepare_extra_fields(**fields: Any) -> dict[str, Any]:
    extra: dict[str, Any] = {}
    for key, value in fields.items():
        if key not in DEFAULT_EXTRA:
            continue
        if value is None:
            continue
        if key in {"user", "session", "node"}:
            extra[key] = str(value)
        elif key == "wish":
            text = str(value)
            extra[key] = text if len(text) <= 60 else text[:60] + "..."
        else:
            extra[key] = str(value)
    return extra


def log_context(**fields: Any):
    extra = _prepare_extra_fields(**fields)
    if not extra:
        return LOGGER.contextualize()
    return LOGGER.contextualize(**extra)


def story_logger(*, trace: str | None = None, user_id: str | None = None,
                 session_id: Any | None = None, node_id: Any | None = None,
                 wish: str | None = None, task: str | None = None):
    extra = dict(DEFAULT_EXTRA)
    extra.update(_prepare_extra_fields(
        trace=trace,
        user=user_id,
        session=session_id,
        node=node_id,
        wish=wish,
        task=task,
    ))
    return LOGGER.bind(**extra)


def kv_text(**fields: Any) -> str:
    parts: list[str] = []
    for key, value in fields.items():
        if value is None or value == "":
            continue
        parts.append(f"{key}={value}")
    return " ".join(parts)


# 全局日志实例
LOGGER = setup_logger()

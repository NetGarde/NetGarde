"""Structured JSON logging for detection-engine (CloudWatch-friendly)."""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Optional


class JsonFormatter(logging.Formatter):
    def __init__(self, service: str):
        super().__init__()
        self._service = service

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "time": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S%z"),
            "service": self._service,
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        for key, value in record.__dict__.items():
            if key.startswith("_") or key in {
                "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
                "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
                "created", "msecs", "relativeCreated", "thread", "threadName",
                "processName", "process", "message", "service",
            }:
                continue
            payload[key] = value
        return json.dumps(payload, ensure_ascii=False)


_LOG_RECORD_RESERVED = frozenset({
    "args", "asctime", "created", "exc_info", "exc_text", "filename",
    "funcName", "levelname", "levelno", "lineno", "message", "module",
    "msecs", "msg", "name", "pathname", "process", "processName",
    "relativeCreated", "stack_info", "thread", "threadName",
})


def structured_extra(event: str, **fields: object) -> dict[str, object]:
    safe: dict[str, object] = {"event": event}
    for key, value in fields.items():
        out_key = f"ctx_{key}" if key in _LOG_RECORD_RESERVED else key
        safe[out_key] = value
    return safe


def setup_logging(
    *,
    service: str,
    logger_name: Optional[str] = None,
) -> logging.Logger:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    use_json = os.getenv("LOG_JSON", "0") == "1"

    root = logging.getLogger()
    if not getattr(root, "_trustedge_configured", False):
        root.handlers.clear()
        root.setLevel(level)
        handler = logging.StreamHandler(sys.stdout)
        if use_json:
            handler.setFormatter(JsonFormatter(service=service))
        else:
            handler.setFormatter(
                logging.Formatter(
                    fmt=f"%(asctime)s %(levelname)s [{service}] %(name)s - %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )
        root.addHandler(handler)
        setattr(root, "_trustedge_configured", True)

    return logging.getLogger(logger_name or service)

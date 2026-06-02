# EN: Shared logger factory for backend modules.
# KO: 백엔드 모듈에서 공통으로 사용하는 Logger 생성기입니다.

import logging
import sys
from app.core.config import settings


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    level = logging.DEBUG if settings.DEBUG else logging.INFO
    logger.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


# PM artifact generation step logger
# 기존 pm_logger.py의 간단한 단계 로그 함수를 backend 공통 logger에 통합했습니다.
from datetime import datetime

def now_text() -> str:
    return datetime.now().strftime("%H:%M:%S")

def log_step(message: str) -> None:
    get_logger("pm_pipeline").info(f"[{now_text()}] {message}")

def log_info(message: str) -> None:
    get_logger("pm_pipeline").info(f"[{now_text()}] {message}")

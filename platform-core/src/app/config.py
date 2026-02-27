import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def get_upstream_url() -> str:
    return os.getenv("PLATFORM_CORE_UPSTREAM_URL", "")


def get_timeout() -> int:
    raw_timeout = os.getenv("PLATFORM_CORE_TIMEOUT", "30")
    try:
        timeout = int(raw_timeout)
    except ValueError as exc:
        raise ValueError("PLATFORM_CORE_TIMEOUT must be a valid integer") from exc
    if timeout <= 0:
        raise ValueError("PLATFORM_CORE_TIMEOUT must be a positive integer")
    return timeout


def get_log_level() -> str:
    log_level = os.getenv("PLATFORM_CORE_LOG_LEVEL", "INFO").strip().upper()
    valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    if log_level not in valid_levels:
        raise ValueError(f"PLATFORM_CORE_LOG_LEVEL must be one of {valid_levels}")
    return log_level

# Platform Core Configuration
PLATFORM_CORE_UPSTREAM_URL: str = get_upstream_url()

def validate_config() -> None:
    if not get_upstream_url().strip():
        raise ValueError("PLATFORM_CORE_UPSTREAM_URL is required and must be set")
    get_timeout()
    get_log_level()

if __name__ == "__main__":
    validate_config()

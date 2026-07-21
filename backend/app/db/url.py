"""PostgreSQL connection URL helpers (Neon-compatible)."""

from __future__ import annotations

from urllib.parse import urlparse


def normalize_database_url(url: str) -> str:
    """Normalize Postgres URLs for SQLAlchemy + psycopg (Neon, Railway, etc.)."""
    if url.startswith("postgres://"):
        url = f"postgresql+psycopg://{url[len('postgres://') :]}"
    elif url.startswith("postgresql://") and "+" not in url.split("://", 1)[0]:
        url = f"postgresql+psycopg://{url[len('postgresql://') :]}"

    parsed = urlparse(url)
    if _requires_ssl(parsed.hostname) and "sslmode=" not in (parsed.query or ""):
        separator = "&" if parsed.query else "?"
        url = f"{url}{separator}sslmode=require"

    return url


def create_engine_kwargs(database_url: str) -> dict:
    """Engine options tuned for cloud Postgres providers."""
    kwargs: dict = {"pool_pre_ping": True}

    if "neon.tech" in database_url.lower():
        # Neon connection limits — keep the pool small; prefer the pooled endpoint in DATABASE_URL.
        kwargs["pool_size"] = 5
        kwargs["max_overflow"] = 0
        # Fail fast instead of hanging indefinitely on unreachable/cold endpoints.
        kwargs["connect_args"] = {"connect_timeout": 10}

    return kwargs


def _requires_ssl(hostname: str | None) -> bool:
    if not hostname:
        return False
    host = hostname.lower()
    return host.endswith(".neon.tech") or host.endswith(".neon.database")

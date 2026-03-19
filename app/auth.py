"""API key authentication."""
from fastapi import Security
from fastapi.security import APIKeyHeader
from starlette.exceptions import HTTPException

from app.config import settings

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def _valid_keys() -> set[str]:
    """Parse comma-separated API_KEYS into a set."""
    if not settings.API_KEYS:
        return set()
    return {k.strip() for k in settings.API_KEYS.split(",") if k.strip()}


async def verify_api_key(api_key: str = Security(API_KEY_HEADER)):
    """Verify API key for API endpoints. Rejects if no keys configured or key not in list."""
    valid = _valid_keys()
    if not valid:
        raise HTTPException(status_code=500, detail="Geen API-sleutels geconfigureerd")
    if not api_key or api_key not in valid:
        raise HTTPException(status_code=403, detail="Ongeldige of ontbrekende API-sleutel")

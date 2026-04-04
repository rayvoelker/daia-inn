"""Async Ollama API client — thin I/O wrapper, returns raw dicts."""

from typing import Any

import httpx


class OllamaClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self._http = httpx.AsyncClient(base_url=base_url, timeout=5.0)

    async def get_version(self) -> dict[str, Any] | None:
        """GET /api/version — returns raw JSON dict or None if unreachable."""
        try:
            resp = await self._http.get("/api/version")
            return resp.json()
        except (httpx.HTTPError, httpx.ConnectError):
            return None

    async def get_running_models(self) -> dict[str, Any] | None:
        """GET /api/ps — returns raw JSON dict or None if unreachable."""
        try:
            resp = await self._http.get("/api/ps")
            return resp.json()
        except (httpx.HTTPError, httpx.ConnectError):
            return None

    async def close(self):
        await self._http.aclose()

import pytest
import httpx
from unittest.mock import AsyncMock, patch
from src.ollama import OllamaClient


@pytest.fixture
def client():
    return OllamaClient("http://ollama:11434")


@pytest.mark.asyncio
async def test_get_version(client):
    mock_response = httpx.Response(200, json={"version": "0.20.0"})
    with patch.object(client._http, "get", new_callable=AsyncMock, return_value=mock_response):
        data = await client.get_version()
    assert data == {"version": "0.20.0"}


@pytest.mark.asyncio
async def test_get_running_models(client):
    payload = {
        "models": [
            {
                "name": "gemma4:26b",
                "size": 24805076992,
                "details": {},
                "size_vram": 24805076992,
            },
        ]
    }
    mock_response = httpx.Response(200, json=payload)
    with patch.object(client._http, "get", new_callable=AsyncMock, return_value=mock_response):
        data = await client.get_running_models()
    assert data["models"][0]["name"] == "gemma4:26b"


@pytest.mark.asyncio
async def test_get_version_unreachable(client):
    with patch.object(client._http, "get", new_callable=AsyncMock, side_effect=httpx.ConnectError("refused")):
        data = await client.get_version()
    assert data is None


@pytest.mark.asyncio
async def test_get_running_models_unreachable(client):
    with patch.object(client._http, "get", new_callable=AsyncMock, side_effect=httpx.ConnectError("refused")):
        data = await client.get_running_models()
    assert data is None

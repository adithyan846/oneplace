import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch

from backend.app import health


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_health_ok_with_mock():
    with patch("backend.app.httpx.AsyncClient") as mock_client_cls:
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"models": []}

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        mock_client_cls.return_value.__aenter__.return_value = mock_client

        result = await health()

        assert result["ok"] is True
        assert result["provider"] == "ollama"
        assert result["base_url"] == "http://127.0.0.1:11434"


@pytest.mark.asyncio
async def test_health_ollama_unavailable():
    with patch("backend.app.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.ConnectError(
            "Connection refused"
        )

        mock_client_cls.return_value.__aenter__.return_value = mock_client

        result = await health()

        assert result["ok"] is False
        assert result["provider"] == "ollama"
        assert result["base_url"] == "http://127.0.0.1:11434"
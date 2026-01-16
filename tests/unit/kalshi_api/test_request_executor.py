"""Tests for kalshi_api request_executor."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from common.kalshi_api.client_helpers.errors import KalshiClientError
from common.kalshi_api.request_executor import RequestExecutor


@pytest.fixture
def mock_session_manager():
    manager = MagicMock()
    manager.initialize = AsyncMock()
    manager.get_session = MagicMock(return_value=MagicMock())
    return manager


@pytest.fixture
def mock_auth_helper():
    helper = MagicMock()
    helper.create_auth_headers.return_value = {"Authorization": "Bearer token"}
    return helper


@pytest.fixture
def executor(mock_session_manager, mock_auth_helper):
    return RequestExecutor(
        session_manager=mock_session_manager,
        auth_helper=mock_auth_helper,
        max_retries=3,
        backoff_base=1.0,
        backoff_max=10.0,
    )


def test_compute_retry_delay_attempt_1(executor):
    delay = executor._compute_retry_delay(1)
    assert delay == 1.0


def test_compute_retry_delay_attempt_2(executor):
    delay = executor._compute_retry_delay(2)
    assert delay == 2.0


def test_compute_retry_delay_attempt_3(executor):
    delay = executor._compute_retry_delay(3)
    assert delay == 4.0


def test_compute_retry_delay_capped_at_max(executor):
    delay = executor._compute_retry_delay(10)
    assert delay == 10.0


def test_compute_retry_delay_invalid_attempt(executor):
    with pytest.raises(TypeError):
        executor._compute_retry_delay(0)


@pytest.mark.asyncio
async def test_execute_request_success(executor, mock_session_manager, mock_auth_helper):
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value='{"success": true}')
    mock_response.json = AsyncMock(return_value={"success": True})

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
    mock_cm.__aexit__ = AsyncMock(return_value=None)

    mock_session = MagicMock()
    mock_session.request.return_value = mock_cm
    mock_session_manager.get_session.return_value = mock_session

    result = await executor.execute_request(
        method_upper="GET",
        url="https://api.kalshi.com/test",
        request_kwargs={},
        path="/test",
        operation_name="test_op",
    )

    assert result == {"success": True}
    mock_session_manager.initialize.assert_called_once()
    mock_auth_helper.create_auth_headers.assert_called_once()


@pytest.mark.asyncio
async def test_execute_request_with_existing_headers(executor, mock_session_manager, mock_auth_helper):
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value="{}")
    mock_response.json = AsyncMock(return_value={})

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
    mock_cm.__aexit__ = AsyncMock(return_value=None)

    mock_session = MagicMock()
    mock_session.request.return_value = mock_cm
    mock_session_manager.get_session.return_value = mock_session

    await executor.execute_request(
        method_upper="GET",
        url="https://api.kalshi.com/test",
        request_kwargs={"headers": {"Custom": "Header"}},
        path="/test",
        operation_name="test_op",
    )

    mock_auth_helper.create_auth_headers.assert_not_called()


@pytest.mark.asyncio
async def test_parse_json_response_success(executor):
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"data": "value"})

    result = await executor._parse_json_response(mock_response, '{"data": "value"}', path="/test")

    assert result == {"data": "value"}


@pytest.mark.asyncio
async def test_parse_json_response_not_json(executor):
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(side_effect=aiohttp.ContentTypeError(MagicMock(), MagicMock()))

    with pytest.raises(KalshiClientError) as exc_info:
        await executor._parse_json_response(mock_response, "not json", path="/test")

    assert "not JSON" in str(exc_info.value)


@pytest.mark.asyncio
async def test_parse_json_response_error_status(executor):
    mock_response = AsyncMock()
    mock_response.status = 400
    mock_response.json = AsyncMock(return_value={"error": "bad request"})

    with pytest.raises(KalshiClientError) as exc_info:
        await executor._parse_json_response(mock_response, '{"error": "bad request"}', path="/test")

    assert "400" in str(exc_info.value)


@pytest.mark.asyncio
async def test_parse_json_response_not_dict(executor):
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=["list", "not", "dict"])

    with pytest.raises(KalshiClientError) as exc_info:
        await executor._parse_json_response(mock_response, '["list"]', path="/test")

    assert "not a JSON object" in str(exc_info.value)


@pytest.mark.asyncio
async def test_execute_request_rate_limited_then_success(mock_session_manager, mock_auth_helper):
    executor = RequestExecutor(
        session_manager=mock_session_manager,
        auth_helper=mock_auth_helper,
        max_retries=3,
        backoff_base=0.001,
        backoff_max=0.01,
    )

    mock_rate_limited_response = MagicMock()
    mock_rate_limited_response.status = 429

    mock_success_response = MagicMock()
    mock_success_response.status = 200
    mock_success_response.text = AsyncMock(return_value='{"success": true}')
    mock_success_response.json = AsyncMock(return_value={"success": True})

    mock_cm_429 = MagicMock()
    mock_cm_429.__aenter__ = AsyncMock(return_value=mock_rate_limited_response)
    mock_cm_429.__aexit__ = AsyncMock(return_value=None)

    mock_cm_200 = MagicMock()
    mock_cm_200.__aenter__ = AsyncMock(return_value=mock_success_response)
    mock_cm_200.__aexit__ = AsyncMock(return_value=None)

    mock_session = MagicMock()
    mock_session.request.side_effect = [mock_cm_429, mock_cm_200]
    mock_session_manager.get_session.return_value = mock_session

    result = await executor.execute_request(
        method_upper="GET",
        url="https://api.kalshi.com/test",
        request_kwargs={},
        path="/test",
        operation_name="test_op",
    )

    assert result == {"success": True}
    assert mock_session.request.call_count == 2


@pytest.mark.asyncio
async def test_execute_request_rate_limited_max_retries(mock_session_manager, mock_auth_helper):
    executor = RequestExecutor(
        session_manager=mock_session_manager,
        auth_helper=mock_auth_helper,
        max_retries=2,
        backoff_base=0.001,
        backoff_max=0.01,
    )

    mock_response = MagicMock()
    mock_response.status = 429

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
    mock_cm.__aexit__ = AsyncMock(return_value=None)

    mock_session = MagicMock()
    mock_session.request.return_value = mock_cm
    mock_session_manager.get_session.return_value = mock_session

    with pytest.raises(KalshiClientError) as exc_info:
        await executor.execute_request(
            method_upper="GET",
            url="https://api.kalshi.com/test",
            request_kwargs={},
            path="/test",
            operation_name="test_op",
        )

    assert "rate limit exceeded" in str(exc_info.value)


@pytest.mark.asyncio
async def test_execute_request_client_error_retry(mock_session_manager, mock_auth_helper):
    executor = RequestExecutor(
        session_manager=mock_session_manager,
        auth_helper=mock_auth_helper,
        max_retries=2,
        backoff_base=0.001,
        backoff_max=0.01,
    )

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(side_effect=aiohttp.ClientError("Connection failed"))
    mock_cm.__aexit__ = AsyncMock(return_value=None)

    mock_session = MagicMock()
    mock_session.request.return_value = mock_cm
    mock_session_manager.get_session.return_value = mock_session

    with pytest.raises(KalshiClientError) as exc_info:
        await executor.execute_request(
            method_upper="GET",
            url="https://api.kalshi.com/test",
            request_kwargs={},
            path="/test",
            operation_name="test_op",
        )

    assert "Connection failed" in str(exc_info.value)
    assert mock_session.request.call_count == 2


@pytest.mark.asyncio
async def test_execute_request_client_error_then_success(mock_session_manager, mock_auth_helper):
    executor = RequestExecutor(
        session_manager=mock_session_manager,
        auth_helper=mock_auth_helper,
        max_retries=3,
        backoff_base=0.001,
        backoff_max=0.01,
    )

    mock_success_response = MagicMock()
    mock_success_response.status = 200
    mock_success_response.text = AsyncMock(return_value='{"success": true}')
    mock_success_response.json = AsyncMock(return_value={"success": True})

    mock_cm_fail = MagicMock()
    mock_cm_fail.__aenter__ = AsyncMock(side_effect=aiohttp.ClientError("Connection failed"))
    mock_cm_fail.__aexit__ = AsyncMock(return_value=None)

    mock_cm_success = MagicMock()
    mock_cm_success.__aenter__ = AsyncMock(return_value=mock_success_response)
    mock_cm_success.__aexit__ = AsyncMock(return_value=None)

    mock_session = MagicMock()
    mock_session.request.side_effect = [mock_cm_fail, mock_cm_success]
    mock_session_manager.get_session.return_value = mock_session

    result = await executor.execute_request(
        method_upper="GET",
        url="https://api.kalshi.com/test",
        request_kwargs={},
        path="/test",
        operation_name="test_op",
    )

    assert result == {"success": True}
    assert mock_session.request.call_count == 2


@pytest.mark.asyncio
async def test_execute_request_server_error_then_success(mock_session_manager, mock_auth_helper):
    executor = RequestExecutor(
        session_manager=mock_session_manager,
        auth_helper=mock_auth_helper,
        max_retries=3,
        backoff_base=0.001,
        backoff_max=0.01,
    )

    mock_server_error_response = MagicMock()
    mock_server_error_response.status = 500

    mock_success_response = MagicMock()
    mock_success_response.status = 200
    mock_success_response.text = AsyncMock(return_value='{"success": true}')
    mock_success_response.json = AsyncMock(return_value={"success": True})

    mock_cm_500 = MagicMock()
    mock_cm_500.__aenter__ = AsyncMock(return_value=mock_server_error_response)
    mock_cm_500.__aexit__ = AsyncMock(return_value=None)

    mock_cm_200 = MagicMock()
    mock_cm_200.__aenter__ = AsyncMock(return_value=mock_success_response)
    mock_cm_200.__aexit__ = AsyncMock(return_value=None)

    mock_session = MagicMock()
    mock_session.request.side_effect = [mock_cm_500, mock_cm_200]
    mock_session_manager.get_session.return_value = mock_session

    result = await executor.execute_request(
        method_upper="GET",
        url="https://api.kalshi.com/test",
        request_kwargs={},
        path="/test",
        operation_name="test_op",
    )

    assert result == {"success": True}
    assert mock_session.request.call_count == 2


@pytest.mark.asyncio
async def test_execute_request_server_error_max_retries(mock_session_manager, mock_auth_helper):
    executor = RequestExecutor(
        session_manager=mock_session_manager,
        auth_helper=mock_auth_helper,
        max_retries=2,
        backoff_base=0.001,
        backoff_max=0.01,
    )

    mock_response = MagicMock()
    mock_response.status = 503

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
    mock_cm.__aexit__ = AsyncMock(return_value=None)

    mock_session = MagicMock()
    mock_session.request.return_value = mock_cm
    mock_session_manager.get_session.return_value = mock_session

    with pytest.raises(KalshiClientError) as exc_info:
        await executor.execute_request(
            method_upper="GET",
            url="https://api.kalshi.com/test",
            request_kwargs={},
            path="/test",
            operation_name="test_op",
        )

    assert "server error 503" in str(exc_info.value)

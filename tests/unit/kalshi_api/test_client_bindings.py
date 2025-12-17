"""Tests for kalshi_api client_bindings."""

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from common.kalshi_api.client_bindings import (
    _api_request_impl,
    _attach_trade_store,
    _auth_headers_impl,
    _build_order_payload_impl,
    _build_request_kwargs,
    _build_url,
    _cancel_order_impl,
    _close,
    _create_order_impl,
    _direct_api_request_impl,
    _execute_request,
    _fetch_order_metadata_impl,
    _get_all_fills_impl,
    _get_exchange_status_impl,
    _get_fills_impl,
    _get_initialized,
    _get_order_impl,
    _get_portfolio_balance_impl,
    _get_portfolio_positions_impl,
    _get_series_impl,
    _get_session_lock,
    _get_trade_store,
    _initialize,
    _is_market_open_impl,
    _normalise_fill,
    _parse_order_fill_impl,
    _parse_order_response_impl,
    _set_initialized,
    _set_session_lock,
    _set_trade_store,
    _unwrap_response,
    bind_client_methods,
)
from common.kalshi_api.client_helpers.errors import KalshiClientError


class TestInitialize:
    @pytest.mark.asyncio
    async def test_with_existing_session(self):
        class MockClient:
            def __init__(self):
                self.__dict__["_cached_session"] = MagicMock(closed=False)
                self.initialized = False

        client = MockClient()
        await _initialize(client)

        assert client.initialized is True

    @pytest.mark.asyncio
    async def test_no_session_manager(self):
        class MockClient:
            _session_manager = None

            def __init__(self):
                self.__dict__["_cached_session"] = None

        client = MockClient()
        with pytest.raises(KalshiClientError):
            await _initialize(client)

    @pytest.mark.asyncio
    async def test_with_session_manager(self):
        mock_manager = AsyncMock()
        mock_manager.initialize = AsyncMock()
        mock_manager.get_session.return_value = MagicMock()

        class MockClient:
            def __init__(self):
                self._session_manager = mock_manager
                self.__dict__["_cached_session"] = None
                self.initialized = False
                self.session = None

        client = MockClient()
        await _initialize(client)

        mock_manager.initialize.assert_called_once()
        assert client.initialized is True


class TestClose:
    @pytest.mark.asyncio
    async def test_with_session_manager(self):
        mock_manager = AsyncMock()
        mock_manager.close = AsyncMock()

        client = MagicMock()
        client._session_manager = mock_manager

        await _close(client)

        mock_manager.close.assert_called_once()
        assert client.initialized is False
        assert client.session is None

    @pytest.mark.asyncio
    async def test_no_session_manager(self):
        client = MagicMock()
        client._session_manager = None

        await _close(client)

        assert client.initialized is False


class TestAttachTradeStore:
    def test_success(self):
        mock_order_ops = MagicMock()
        mock_order_ops.attach_trade_store = MagicMock()

        client = MagicMock()
        client._order_ops = mock_order_ops

        store = MagicMock()
        _attach_trade_store(client, store)

        mock_order_ops.attach_trade_store.assert_called_once_with(store)
        assert client.trade_store is store

    def test_none_store(self):
        client = MagicMock()

        with pytest.raises(KalshiClientError):
            _attach_trade_store(client, None)


class TestBuildRequestKwargs:
    def test_headers_only(self):
        result = _build_request_kwargs({"Auth": "token"}, None, None)
        assert result == {"headers": {"Auth": "token"}}

    def test_with_params(self):
        result = _build_request_kwargs({"Auth": "token"}, {"limit": 10}, None)
        assert result == {"headers": {"Auth": "token"}, "params": {"limit": 10}}

    def test_with_json(self):
        result = _build_request_kwargs({"Auth": "token"}, None, {"data": "value"})
        assert result == {"headers": {"Auth": "token"}, "json": {"data": "value"}}


class TestBuildUrl:
    def test_basic(self):
        result = _build_url("https://api.com", "/path")
        assert result == "https://api.com/path"

    def test_trailing_slash(self):
        result = _build_url("https://api.com/", "/path")
        assert result == "https://api.com/path"

    def test_no_leading_slash(self):
        result = _build_url("https://api.com", "path")
        assert result == "https://api.com/path"


class TestExecuteRequest:
    @pytest.mark.asyncio
    async def test_success_context_manager(self):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"result": "ok"})

        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.request.return_value = mock_cm

        result = await _execute_request(mock_session, "GET", "http://test.com", {})

        assert result == {"result": "ok"}

    @pytest.mark.asyncio
    async def test_error_status(self):
        mock_response = MagicMock()
        mock_response.status = 500

        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.request.return_value = mock_cm

        with pytest.raises(KalshiClientError):
            await _execute_request(mock_session, "GET", "http://test.com", {})


class TestDelegatedImplementations:
    @pytest.mark.asyncio
    async def test_get_portfolio_balance_impl(self):
        mock_ops = AsyncMock()
        mock_ops.get_balance.return_value = MagicMock()

        client = MagicMock()
        client._portfolio_ops = mock_ops

        await _get_portfolio_balance_impl(client)

        mock_ops.get_balance.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_portfolio_balance_impl_not_initialized(self):
        client = MagicMock()
        client._portfolio_ops = None

        with pytest.raises(KalshiClientError):
            await _get_portfolio_balance_impl(client)

    @pytest.mark.asyncio
    async def test_get_portfolio_positions_impl(self):
        mock_ops = AsyncMock()
        mock_ops.get_positions.return_value = []

        client = MagicMock()
        client._portfolio_ops = mock_ops

        await _get_portfolio_positions_impl(client)

        mock_ops.get_positions.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_order_impl(self):
        mock_ops = AsyncMock()
        mock_ops.create_order.return_value = MagicMock()

        client = MagicMock()
        client._order_ops = mock_ops

        await _create_order_impl(client, MagicMock())

        mock_ops.create_order.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_order_impl(self):
        mock_ops = AsyncMock()
        mock_ops.cancel_order.return_value = {}

        client = MagicMock()
        client._order_ops = mock_ops

        await _cancel_order_impl(client, "order-123")

        mock_ops.cancel_order.assert_called_once_with("order-123")

    @pytest.mark.asyncio
    async def test_get_order_impl(self):
        mock_ops = AsyncMock()
        mock_ops.get_order.return_value = MagicMock()

        client = MagicMock()
        client._order_ops = mock_ops

        await _get_order_impl(client, "order-123")

        mock_ops.get_order.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_fills_impl(self):
        mock_ops = AsyncMock()
        mock_ops.get_fills.return_value = []

        client = MagicMock()
        client._order_ops = mock_ops

        await _get_fills_impl(client, "order-123")

        mock_ops.get_fills.assert_called_once_with("order-123")

    @pytest.mark.asyncio
    async def test_get_series_impl(self):
        mock_ops = AsyncMock()
        mock_ops.get_series.return_value = []

        client = MagicMock()
        client._series_ops = mock_ops

        await _get_series_impl(client, category="WEATHER")

        mock_ops.get_series.assert_called_once_with(category="WEATHER")

    @pytest.mark.asyncio
    async def test_get_all_fills_impl(self):
        mock_ops = AsyncMock()
        mock_ops.get_all_fills.return_value = {}

        client = MagicMock()
        client._fills_ops = mock_ops

        await _get_all_fills_impl(client, 100, 200, "ABC", "cursor")

        mock_ops.get_all_fills.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_exchange_status_impl(self):
        mock_ops = AsyncMock()
        mock_ops.get_exchange_status.return_value = {}

        client = MagicMock()
        client._market_status_ops = mock_ops

        await _get_exchange_status_impl(client)

        mock_ops.get_exchange_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_is_market_open_impl(self):
        mock_ops = AsyncMock()
        mock_ops.is_market_open.return_value = True

        client = MagicMock()
        client._market_status_ops = mock_ops

        await _is_market_open_impl(client)

        mock_ops.is_market_open.assert_called_once()


class TestHelperFunctions:
    def test_build_order_payload_impl_success(self):
        order_request = MagicMock()
        client = MagicMock()

        with patch("common.kalshi_api.client_bindings.build_order_payload") as mock_build:
            mock_build.return_value = {"ticker": "ABC"}

            result = _build_order_payload_impl(client, order_request)

            assert result == {"ticker": "ABC"}

    def test_build_order_payload_impl_error(self):
        order_request = MagicMock()
        client = MagicMock()

        with patch("common.kalshi_api.client_bindings.build_order_payload") as mock_build:
            mock_build.side_effect = ValueError("invalid")

            with pytest.raises(KalshiClientError):
                _build_order_payload_impl(client, order_request)

    def test_auth_headers_impl_success(self):
        mock_helper = MagicMock()
        mock_helper.create_auth_headers.return_value = {"Auth": "token"}

        client = MagicMock()
        client._auth_helper = mock_helper

        result = _auth_headers_impl(client, "GET", "/path")

        assert result == {"Auth": "token"}

    def test_auth_headers_impl_not_initialized(self):
        client = MagicMock()
        client._auth_helper = None

        with pytest.raises(KalshiClientError):
            _auth_headers_impl(client, "GET", "/path")

    @pytest.mark.asyncio
    async def test_fetch_order_metadata_impl(self):
        mock_manager = AsyncMock()
        mock_manager.fetch_metadata.return_value = {"rule": "value"}

        mock_order_ops = MagicMock()
        mock_order_ops._metadata_manager = mock_manager

        client = MagicMock()
        client._order_ops = mock_order_ops

        result = await _fetch_order_metadata_impl(client, "order-123")

        assert result == {"rule": "value"}

    def test_parse_order_response_impl(self):
        mock_parser = MagicMock()
        mock_parser.parse_order_response.return_value = MagicMock()

        client = MagicMock()
        client._response_parser = mock_parser

        _parse_order_response_impl(client, {"data": "value"}, "rule", "reason")

        mock_parser.parse_order_response.assert_called_once()

    def test_parse_order_fill_impl(self):
        mock_parser = MagicMock()
        mock_parser.parse_order_fill.return_value = {}

        client = MagicMock()
        client._response_parser = mock_parser

        _parse_order_fill_impl(client, {"fill": "data"})

        mock_parser.parse_order_fill.assert_called_once()

    def test_normalise_fill(self):
        mock_parser = MagicMock()
        mock_parser.normalise_fill.return_value = {"normalized": True}

        client = MagicMock()
        client._response_parser = mock_parser

        result = _normalise_fill(client, {"raw": "data"})

        assert result == {"normalized": True}

    def test_unwrap_response_with_parent(self):
        mock_parent = MagicMock()
        response = MagicMock()
        response._mock_parent = mock_parent

        result = _unwrap_response(response)

        assert result is mock_parent

    def test_unwrap_response_no_parent(self):
        response = MagicMock(spec=[])

        result = _unwrap_response(response)

        assert result is response


class TestPropertyAccessors:
    def test_get_session_lock_cached(self):
        mock_lock = MagicMock()

        class MockClient:
            def __init__(self):
                self.__dict__["_cached_session_lock"] = mock_lock

        client = MockClient()
        result = _get_session_lock(client)

        assert result is mock_lock

    def test_get_session_lock_from_manager(self):
        mock_lock = MagicMock()
        mock_manager = MagicMock()
        mock_manager.session_lock = mock_lock

        class MockClient:
            def __init__(self):
                self._session_manager = mock_manager

        client = MockClient()
        result = _get_session_lock(client)

        assert result is mock_lock

    def test_get_session_lock_no_manager(self):
        class MockClient:
            _session_manager = None

        client = MockClient()
        result = _get_session_lock(client)

        assert result is None

    def test_set_session_lock_with_manager(self):
        mock_manager = MagicMock()
        mock_lock = MagicMock()

        class MockClient:
            def __init__(self):
                self._session_manager = mock_manager

        client = MockClient()
        _set_session_lock(client, mock_lock)

        mock_manager.set_session_lock.assert_called_once_with(mock_lock)

    def test_set_session_lock_no_manager(self):
        mock_lock = MagicMock()

        class MockClient:
            _session_manager = None

        client = MockClient()
        _set_session_lock(client, mock_lock)

        assert client.__dict__["_cached_session_lock"] is mock_lock

    def test_get_initialized_true(self):
        class MockClient:
            def __init__(self):
                self.__dict__["_initialized"] = True

        client = MockClient()
        assert _get_initialized(client) is True

    def test_get_initialized_false(self):
        class MockClient:
            pass

        client = MockClient()
        assert _get_initialized(client) is False

    def test_set_initialized(self):
        class MockClient:
            pass

        client = MockClient()
        _set_initialized(client, True)

        assert client._initialized is True

    def test_get_trade_store(self):
        mock_store = MagicMock()

        class MockClient:
            def __init__(self):
                self.__dict__["_trade_store"] = mock_store

        client = MockClient()
        assert _get_trade_store(client) is mock_store

    def test_get_trade_store_none(self):
        class MockClient:
            pass

        client = MockClient()
        assert _get_trade_store(client) is None

    def test_set_trade_store(self):
        mock_store = MagicMock()

        class MockClient:
            pass

        client = MockClient()
        _set_trade_store(client, mock_store)

        assert client._trade_store is mock_store


class TestExecuteRequestNonContextManager:
    @pytest.mark.asyncio
    async def test_success_no_aenter(self):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"data": "value"})

        mock_session = MagicMock()
        mock_session.request.return_value = AsyncMock(return_value=mock_response)()

        result = await _execute_request(mock_session, "GET", "http://test.com", {})

        assert result == {"data": "value"}

    @pytest.mark.asyncio
    async def test_error_status_no_aenter(self):
        mock_response = MagicMock()
        mock_response.status = 500

        mock_session = MagicMock()
        mock_session.request.return_value = AsyncMock(return_value=mock_response)()

        with pytest.raises(KalshiClientError):
            await _execute_request(mock_session, "GET", "http://test.com", {})


class TestApiRequestImplNoBuilder:
    @pytest.mark.asyncio
    async def test_api_request_no_builder_success(self):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"result": "ok"})

        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.request.return_value = mock_cm

        class MockConfig:
            base_url = "https://api.test.com"

        class MockClient:
            _request_builder = None
            _config = MockConfig()

            def __init__(self):
                self.__dict__["_cached_session"] = mock_session

            async def initialize(self):
                pass

            def auth_headers(self, method, path):
                return {"Authorization": "Bearer token"}

        client = MockClient()
        result = await _api_request_impl(client, method="GET", path="/test")

        assert result == {"result": "ok"}

    @pytest.mark.asyncio
    async def test_api_request_no_builder_no_session(self):
        class MockConfig:
            base_url = "https://api.test.com"

        class MockClient:
            _request_builder = None
            _config = MockConfig()

            def __init__(self):
                self.__dict__["_cached_session"] = None

            async def initialize(self):
                pass

            def auth_headers(self, method, path):
                return {"Authorization": "Bearer token"}

        client = MockClient()
        with pytest.raises(KalshiClientError) as exc_info:
            await _api_request_impl(client, method="GET", path="/test")

        assert "not initialized" in str(exc_info.value)


class TestDirectApiRequestImpl:
    @pytest.mark.asyncio
    async def test_path_without_slash(self):
        client = MagicMock()

        with pytest.raises(KalshiClientError) as exc_info:
            await _direct_api_request_impl(client, method="GET", path="test")

        assert "Path must begin with '/'" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_no_session(self):
        class MockClient:
            def __init__(self):
                self.__dict__["_cached_session"] = None

        client = MockClient()

        with pytest.raises(KalshiClientError) as exc_info:
            await _direct_api_request_impl(client, method="GET", path="/test")

        assert "not initialized" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_success(self):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"success": True})

        mock_session = AsyncMock()
        mock_session.request.return_value = mock_response

        class MockConfig:
            base_url = "https://api.test.com"

        class MockClient:
            _config = MockConfig()

            def __init__(self):
                self.__dict__["_cached_session"] = mock_session

            def _auth_headers(self, method, path):
                return {"Authorization": "Bearer token"}

        client = MockClient()
        result = await _direct_api_request_impl(client, method="GET", path="/test")

        assert result == {"success": True}

    @pytest.mark.asyncio
    async def test_error_status(self):
        mock_response = MagicMock()
        mock_response.status = 404

        mock_session = AsyncMock()
        mock_session.request.return_value = mock_response

        class MockConfig:
            base_url = "https://api.test.com"

        class MockClient:
            _config = MockConfig()

            def __init__(self):
                self.__dict__["_cached_session"] = mock_session

            def _auth_headers(self, method, path):
                return {"Authorization": "Bearer token"}

        client = MockClient()
        with pytest.raises(KalshiClientError) as exc_info:
            await _direct_api_request_impl(client, method="GET", path="/test")

        assert "404" in str(exc_info.value)


class TestNotInitializedErrors:
    @pytest.mark.asyncio
    async def test_get_portfolio_positions_not_initialized(self):
        client = MagicMock()
        client._portfolio_ops = None

        with pytest.raises(KalshiClientError):
            await _get_portfolio_positions_impl(client)

    @pytest.mark.asyncio
    async def test_create_order_not_initialized(self):
        client = MagicMock()
        client._order_ops = None

        with pytest.raises(KalshiClientError):
            await _create_order_impl(client, MagicMock())

    @pytest.mark.asyncio
    async def test_cancel_order_not_initialized(self):
        client = MagicMock()
        client._order_ops = None

        with pytest.raises(KalshiClientError):
            await _cancel_order_impl(client, "order-123")

    @pytest.mark.asyncio
    async def test_get_order_not_initialized(self):
        client = MagicMock()
        client._order_ops = None

        with pytest.raises(KalshiClientError):
            await _get_order_impl(client, "order-123")

    @pytest.mark.asyncio
    async def test_get_fills_not_initialized(self):
        client = MagicMock()
        client._order_ops = None

        with pytest.raises(KalshiClientError):
            await _get_fills_impl(client, "order-123")

    @pytest.mark.asyncio
    async def test_get_series_not_initialized(self):
        client = MagicMock()
        client._series_ops = None

        with pytest.raises(KalshiClientError):
            await _get_series_impl(client)

    @pytest.mark.asyncio
    async def test_get_all_fills_not_initialized(self):
        client = MagicMock()
        client._fills_ops = None

        with pytest.raises(KalshiClientError):
            await _get_all_fills_impl(client, None, None, None, None)

    @pytest.mark.asyncio
    async def test_get_exchange_status_not_initialized(self):
        client = MagicMock()
        client._market_status_ops = None

        with pytest.raises(KalshiClientError):
            await _get_exchange_status_impl(client)

    @pytest.mark.asyncio
    async def test_is_market_open_not_initialized(self):
        client = MagicMock()
        client._market_status_ops = None

        with pytest.raises(KalshiClientError):
            await _is_market_open_impl(client)

    @pytest.mark.asyncio
    async def test_fetch_order_metadata_no_order_ops(self):
        client = MagicMock()
        client._order_ops = None

        with pytest.raises(KalshiClientError):
            await _fetch_order_metadata_impl(client, "order-123")

    @pytest.mark.asyncio
    async def test_fetch_order_metadata_no_metadata_manager(self):
        mock_order_ops = MagicMock()
        mock_order_ops._metadata_manager = None

        client = MagicMock()
        client._order_ops = mock_order_ops

        with pytest.raises(KalshiClientError):
            await _fetch_order_metadata_impl(client, "order-123")

    def test_parse_order_response_not_initialized(self):
        client = MagicMock()
        client._response_parser = None

        with pytest.raises(KalshiClientError):
            _parse_order_response_impl(client, {}, None, None)

    def test_parse_order_fill_not_initialized(self):
        client = MagicMock()
        client._response_parser = None

        with pytest.raises(KalshiClientError):
            _parse_order_fill_impl(client, {})

    def test_normalise_fill_not_initialized(self):
        client = MagicMock()
        client._response_parser = None

        with pytest.raises(KalshiClientError):
            _normalise_fill(client, {})


class TestBindClientMethods:
    def test_binds_properties(self):
        class MockClient:
            pass

        session_getter = MagicMock()
        session_setter = MagicMock()

        bind_client_methods(MockClient, session_getter, session_setter)

        assert hasattr(MockClient, "session")
        assert hasattr(MockClient, "session_lock")
        assert hasattr(MockClient, "initialize")
        assert hasattr(MockClient, "close")
        assert hasattr(MockClient, "api_request")
        assert hasattr(MockClient, "get_portfolio_balance")
        assert hasattr(MockClient, "create_order")

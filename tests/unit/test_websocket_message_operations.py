import pytest

from src.common.websocket_connection_manager_helpers.message_operations import (
    WebSocketMessageOperations,
)


class DummyConnectionProvider:
    def __init__(self, websocket):
        self._websocket = websocket

    def get_connection(self):
        return self._websocket


class DummyWebSocket:
    def __init__(
        self,
        *,
        close_code=None,
        send_exception: Exception | None = None,
        recv_exception: Exception | None = None,
        recv_value=None,
    ):
        self.close_code = close_code
        self._send_exception = send_exception
        self._recv_exception = recv_exception
        self._recv_value = recv_value
        self.sent_messages: list[str] = []

    async def send(self, message: str):
        if self._send_exception:
            raise self._send_exception
        self.sent_messages.append(message)

    async def recv(self):
        if self._recv_exception:
            raise self._recv_exception
        return self._recv_value


@pytest.mark.asyncio
async def test_send_message_returns_false_when_disconnected():
    ops = WebSocketMessageOperations("svc", DummyConnectionProvider(None))

    result = await ops.send_message("hello")

    assert result is False


@pytest.mark.asyncio
async def test_send_message_handles_transport_error():
    websocket = DummyWebSocket(send_exception=OSError("network down"))
    ops = WebSocketMessageOperations("svc", DummyConnectionProvider(websocket))

    result = await ops.send_message("payload")

    assert result is False
    assert websocket.sent_messages == []


@pytest.mark.asyncio
async def test_receive_message_returns_none_when_closed():
    websocket = DummyWebSocket(close_code=1000)
    ops = WebSocketMessageOperations("svc", DummyConnectionProvider(websocket))

    result = await ops.receive_message()

    assert result is None


@pytest.mark.asyncio
async def test_receive_message_handles_generic_error():
    websocket = DummyWebSocket(recv_exception=RuntimeError("boom"))
    ops = WebSocketMessageOperations("svc", DummyConnectionProvider(websocket))

    result = await ops.receive_message()

    assert result is None


@pytest.mark.asyncio
async def test_receive_message_decodes_bytes_payload():
    websocket = DummyWebSocket(recv_value=b"data")
    ops = WebSocketMessageOperations("svc", DummyConnectionProvider(websocket))

    result = await ops.receive_message()

    assert result == "data"

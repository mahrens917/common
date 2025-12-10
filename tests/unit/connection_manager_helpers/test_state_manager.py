"""Tests for the StateManager stub."""

import pytest

from common.connection_manager_helpers.state_manager import StateManager


class TestStateManager:
    def test_init_stores_kwargs_and_defaults_flag(self) -> None:
        manager = StateManager(context="ctx", state="ready")

        assert manager.context == "ctx"
        assert manager.state == "ready"
        assert manager._shutdown_requested is False

    def test_request_shutdown_marks_flag(self) -> None:
        manager = StateManager()

        manager.request_shutdown()

        assert manager._shutdown_requested is True

    @pytest.mark.asyncio
    async def test_transition_state_stub_raises(self) -> None:
        manager = StateManager()

        with pytest.raises(NotImplementedError):
            await manager.transition_state("state")

"""Tests for checker registry."""

from __future__ import annotations

from src.common.error_analyzer_helpers.data_classes import ErrorCategory
from src.common.error_analyzer_helpers.error_categorizer_helpers.checker_registry import (
    CheckerRegistry,
)


class TestCheckerRegistry:
    """Tests for CheckerRegistry class."""

    def test_category_checkers_is_list(self) -> None:
        """CATEGORY_CHECKERS is a list."""
        assert isinstance(CheckerRegistry.CATEGORY_CHECKERS, list)

    def test_category_checkers_has_tuples(self) -> None:
        """CATEGORY_CHECKERS contains tuples."""
        for item in CheckerRegistry.CATEGORY_CHECKERS:
            assert isinstance(item, tuple)
            assert len(item) == 2

    def test_category_checkers_first_element_is_error_category(self) -> None:
        """First element of each tuple is ErrorCategory."""
        for category, _ in CheckerRegistry.CATEGORY_CHECKERS:
            assert isinstance(category, ErrorCategory)

    def test_category_checkers_second_element_is_string(self) -> None:
        """Second element of each tuple is a string method name."""
        for _, method_name in CheckerRegistry.CATEGORY_CHECKERS:
            assert isinstance(method_name, str)
            assert method_name.startswith("_is_")
            assert method_name.endswith("_error")

    def test_category_checkers_includes_websocket(self) -> None:
        """CATEGORY_CHECKERS includes WEBSOCKET category."""
        categories = [cat for cat, _ in CheckerRegistry.CATEGORY_CHECKERS]
        assert ErrorCategory.WEBSOCKET in categories

    def test_category_checkers_includes_api(self) -> None:
        """CATEGORY_CHECKERS includes API category."""
        categories = [cat for cat, _ in CheckerRegistry.CATEGORY_CHECKERS]
        assert ErrorCategory.API in categories

    def test_category_checkers_includes_dependency(self) -> None:
        """CATEGORY_CHECKERS includes DEPENDENCY category."""
        categories = [cat for cat, _ in CheckerRegistry.CATEGORY_CHECKERS]
        assert ErrorCategory.DEPENDENCY in categories

    def test_category_checkers_includes_network(self) -> None:
        """CATEGORY_CHECKERS includes NETWORK category."""
        categories = [cat for cat, _ in CheckerRegistry.CATEGORY_CHECKERS]
        assert ErrorCategory.NETWORK in categories

    def test_category_checkers_includes_authentication(self) -> None:
        """CATEGORY_CHECKERS includes AUTHENTICATION category."""
        categories = [cat for cat, _ in CheckerRegistry.CATEGORY_CHECKERS]
        assert ErrorCategory.AUTHENTICATION in categories

    def test_category_checkers_includes_data(self) -> None:
        """CATEGORY_CHECKERS includes DATA category."""
        categories = [cat for cat, _ in CheckerRegistry.CATEGORY_CHECKERS]
        assert ErrorCategory.DATA in categories

    def test_category_checkers_includes_configuration(self) -> None:
        """CATEGORY_CHECKERS includes CONFIGURATION category."""
        categories = [cat for cat, _ in CheckerRegistry.CATEGORY_CHECKERS]
        assert ErrorCategory.CONFIGURATION in categories

    def test_category_checkers_includes_resource(self) -> None:
        """CATEGORY_CHECKERS includes RESOURCE category."""
        categories = [cat for cat, _ in CheckerRegistry.CATEGORY_CHECKERS]
        assert ErrorCategory.RESOURCE in categories

    def test_websocket_is_first_checker(self) -> None:
        """WEBSOCKET checker is first (most specific)."""
        first_category, _ = CheckerRegistry.CATEGORY_CHECKERS[0]
        assert first_category == ErrorCategory.WEBSOCKET

    def test_resource_is_last_checker(self) -> None:
        """RESOURCE checker is last (least specific)."""
        last_category, _ = CheckerRegistry.CATEGORY_CHECKERS[-1]
        assert last_category == ErrorCategory.RESOURCE

    def test_has_eight_checkers(self) -> None:
        """Registry has eight checkers."""
        assert len(CheckerRegistry.CATEGORY_CHECKERS) == 8

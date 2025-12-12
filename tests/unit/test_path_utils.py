"""Tests for path_utils module."""

import pytest
from pathlib import Path

from common.path_utils import get_project_root


class TestGetProjectRoot:
    """Tests for get_project_root function."""

    def test_gets_project_root_with_default_levels(self):
        """Test getting project root with default levels_up=2."""
        result = get_project_root(__file__)
        assert isinstance(result, Path)
        assert result.exists()

    def test_gets_project_root_with_custom_levels(self):
        """Test getting project root with custom levels_up."""
        result = get_project_root(__file__, levels_up=1)
        assert isinstance(result, Path)
        assert result.exists()

    def test_raises_value_error_when_levels_exceed_depth(self):
        """Test that ValueError is raised when levels_up exceeds directory depth."""
        with pytest.raises(ValueError, match="Cannot ascend .* levels"):
            get_project_root(__file__, levels_up=100)

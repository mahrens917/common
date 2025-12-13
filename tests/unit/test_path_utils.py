from __future__ import annotations

from pathlib import Path

import pytest

from common.path_utils import get_project_root


def test_get_project_root_returns_expected_parent(tmp_path: Path):
    nested = tmp_path / "a" / "b" / "c" / "file.py"
    nested.parent.mkdir(parents=True)
    nested.write_text("x")

    assert get_project_root(nested, levels_up=2) == tmp_path / "a"


def test_get_project_root_raises_when_levels_exceed_depth(tmp_path: Path):
    file_path = tmp_path / "file.py"
    file_path.write_text("x")

    with pytest.raises(ValueError):
        get_project_root(file_path, levels_up=10)

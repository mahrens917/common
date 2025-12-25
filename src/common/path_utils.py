"""Filesystem path helpers shared across services."""

from __future__ import annotations

from pathlib import Path
from typing import Union


def get_project_root(reference_file: Union[str, Path], *, levels_up: int = 2) -> Path:
    """
    Return the project root by walking ``levels_up`` directories from ``reference_file``.

    Args:
        reference_file: Caller ``__file__`` to anchor path resolution.
        levels_up: Number of parent directories to ascend (default: 2).

    Raises:
        ValueError: If ``levels_up`` exceeds the available parent depth.
    """
    base_path = Path(reference_file).resolve()
    try:
        return base_path.parents[levels_up]
    except IndexError as exc:
        raise ValueError(f"Cannot ascend {levels_up} levels from {base_path}; adjust levels_up.") from exc

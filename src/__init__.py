"""Namespace package shim for src-layout imports.

This repo references sibling packages like `src.kalshi` in development environments.
Using `pkgutil.extend_path` allows this `src` package to be split across multiple
directories on `sys.path`.
"""

from __future__ import annotations

from pkgutil import extend_path

__path__ = extend_path(__path__, __name__)  # type: ignore[name-defined]

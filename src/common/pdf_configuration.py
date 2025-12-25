from __future__ import annotations

"""
Centralized PDF configuration loading.

Provides a merged view of baseline and optimized PDF parameters. Runtime calls
resolve the snapshot for the active currency.
"""

import contextlib
import json
from contextvars import ContextVar, Token
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# Constants
PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASE_CONFIG_PATH = PROJECT_ROOT / "config" / "pdf_parameters.json"
_CURRENT_CURRENCY: ContextVar[Optional[str]] = ContextVar("pdf_current_currency")
_CURRENT_CURRENCY.set(None)

_OPTIMIZED_FILENAME_TEMPLATE = "pdf_parameters.optimized.{currency}.json"
NDIM_2D = 2
_DEFAULT_METADATA = {}


class PDFConfigurationMissing(FileNotFoundError):
    """Raised when the optimized PDF configuration snapshot is unavailable."""


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise ValueError(f"Invalid JSON in configuration file {path}") from exc


def _deep_merge_dict(base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively merge ``overlay`` into ``base``.

    Lists are replaced wholesale; dictionaries are merged key-by-key.
    """
    result = deepcopy(base)
    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge_dict(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def _normalize_currency(currency: str) -> str:
    normalized = currency.strip().upper()
    if not normalized:
        raise ValueError("Currency identifier cannot be empty.")
    return normalized


class PDFConfigurationCurrencyUnset(RuntimeError):
    """Raised when configuration is requested without an active currency."""


def _resolve_currency(currency: Optional[str]) -> str:
    candidate = currency or _CURRENT_CURRENCY.get()
    if not candidate:
        raise PDFConfigurationCurrencyUnset(
            "PDF configuration requested without specifying a currency. " "Set the currency context or provide a currency argument."
        )
    return _normalize_currency(candidate)


def _optimized_config_path(currency: str) -> Path:
    normalized = _normalize_currency(currency)
    filename = _OPTIMIZED_FILENAME_TEMPLATE.format(currency=normalized)
    return PROJECT_ROOT / "config" / filename


def load_active_pdf_config(currency: Optional[str] = None, *, allow_missing: bool = False) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Load the active PDF configuration with optimized overrides applied.

    Args:
        currency: Optional currency code to resolve overrides. If omitted, the value
            from the current currency context is used.

    Returns:
        Tuple of (merged_config, optimized_metadata)

    Raises:
        PDFConfigurationCurrencyUnset: If no currency context or argument is provided.
        PDFConfigurationMissing: If the optimized snapshot is absent.
    """
    resolved_currency = _resolve_currency(currency)
    base_config = _load_json(BASE_CONFIG_PATH)

    optimized_path = _optimized_config_path(resolved_currency)
    optimized_missing = not optimized_path.exists()

    if optimized_missing and not allow_missing:
        raise PDFConfigurationMissing(
            f"Optimized PDF configuration missing for {resolved_currency}: {optimized_path}. "
            "Run the optimizer to generate it before executing the pipeline."
        )

    optimized_blob: Dict[str, Any]
    if optimized_missing:
        optimized_blob = {"parameters": {}, "metadata": {"currency": resolved_currency}}
    else:
        optimized_blob = _load_json(optimized_path)

    parameters_val = optimized_blob.get("parameters")
    if parameters_val:
        parameters = parameters_val
    else:
        parameters = {}
    if not parameters and not optimized_missing:
        raise ValueError(f"Optimized configuration {optimized_path} must provide a 'parameters' object.")

    merged_config = _deep_merge_dict(base_config, parameters)
    metadata = {key: value for key, value in optimized_blob.items() if key != "parameters"}
    metadata.setdefault("currency", resolved_currency)

    return merged_config, metadata


def load_base_pdf_config() -> Dict[str, Any]:
    """Return the baseline pdf_parameters.json contents."""
    return _load_json(BASE_CONFIG_PATH)


def get_active_config_paths(currency: Optional[str] = None) -> Tuple[Path, Path]:
    """Return the baseline and optimized config paths for the resolved currency."""

    resolved_currency = _resolve_currency(currency)
    optimized_path = _optimized_config_path(resolved_currency)

    if not optimized_path.exists():
        raise PDFConfigurationMissing(f"Optimized PDF configuration missing for {resolved_currency}: {optimized_path}")
    return BASE_CONFIG_PATH, optimized_path


def write_optimized_snapshot(payload: Dict[str, Any], currency: str) -> Path:
    """
    Persist the optimizer snapshot to disk for the specified currency.

    Args:
        payload: Serializable dictionary containing metadata and parameters.
        currency: Currency code the snapshot applies to.

    Returns:
        Path pointing to the optimized configuration snapshot.
    """
    resolved_currency = _normalize_currency(currency)
    optimized_path = _optimized_config_path(resolved_currency)
    optimized_path.parent.mkdir(parents=True, exist_ok=True)

    metadata = payload.setdefault("metadata", _DEFAULT_METADATA)
    metadata.setdefault("currency", resolved_currency)

    with optimized_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=NDIM_2D, sort_keys=True)
        handle.write("\n")

    return optimized_path


def set_current_currency(currency: Optional[str]) -> Token:
    """Set the active currency in the context and return the context token."""
    normalized = None if currency is None else _normalize_currency(currency)
    return _CURRENT_CURRENCY.set(normalized)


def reset_current_currency(token: Token) -> None:
    """Reset the active currency context to a previous token."""
    _CURRENT_CURRENCY.reset(token)


@contextlib.contextmanager
def currency_context(currency: str):
    """
    Context manager for temporarily setting the active currency.

    Ensures nested calls restore the previous currency when the context exits.
    """
    token = set_current_currency(currency)
    try:
        yield
    finally:
        reset_current_currency(token)

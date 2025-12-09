"""Helper modules for error categorization."""

from .checker_dispatcher import dispatch_category_check
from .checker_registry import CheckerRegistry
from .signature_adapter import SignatureAdapter

__all__ = ["CheckerRegistry", "SignatureAdapter", "dispatch_category_check"]

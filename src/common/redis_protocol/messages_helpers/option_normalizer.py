"""Option type normalization helper"""

from typing import Optional


def normalize_option_type(option_type: Optional[str], option_kind: Optional[str] = None) -> Optional[str]:
    """
    Normalize option type to standard format (call/put).

    Args:
        option_type: Primary option type string (may be abbreviated)
        option_kind: Alternate option kind string if option_type is not provided

    Returns:
        Normalized option type ('call' or 'put') or None
    """
    candidate = option_type
    if not candidate:
        candidate = option_kind
    if not candidate:
        return None
    lowered = str(candidate).strip().lower()
    if lowered.startswith("c"):
        return "call"
    if lowered.startswith("p"):
        return "put"
    return None

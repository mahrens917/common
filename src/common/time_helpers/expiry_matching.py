"""Expiry matching and finding utilities."""

from datetime import datetime
from typing import List, Optional, Union

from common.exceptions import ValidationError

from .expiry_wrapper import DateTimeExpiry


def find_closest_expiry(
    expiries: List[Union[DateTimeExpiry, datetime, str, float]],
    target: Union[DateTimeExpiry, datetime, str, float],
) -> Optional[Union[DateTimeExpiry, datetime, str, float]]:
    """Find the closest expiry to ``target``."""
    if not expiries:
        return None

    if not isinstance(target, DateTimeExpiry):
        target = DateTimeExpiry(target)

    expiry_objects = []
    for expiry in expiries:
        if isinstance(expiry, DateTimeExpiry):
            expiry_objects.append((expiry, expiry.datetime_value))
        else:
            try:
                obj = DateTimeExpiry(expiry)
            except (  # policy_guard: allow-silent-handler
                TypeError,
                ValueError,
                ValidationError,
            ):
                continue
            expiry_objects.append((obj, expiry))

    if not expiry_objects:
        return None

    closest_idx = min(
        range(len(expiry_objects)),
        key=lambda idx: abs((expiry_objects[idx][0].datetime_value - target.datetime_value).total_seconds()),
    )

    return expiry_objects[closest_idx][1]


def match_expiries_exactly(
    expiries: List[Union[DateTimeExpiry, datetime, str, float]],
    target: Union[DateTimeExpiry, datetime, str, float],
) -> List[Union[DateTimeExpiry, datetime, str, float]]:
    """Return exact matches for the target expiry."""
    if not expiries:
        return []

    if not isinstance(target, DateTimeExpiry):
        target = DateTimeExpiry(target)

    matches: List[Union[DateTimeExpiry, datetime, str, float]] = []
    for expiry in expiries:
        try:
            candidate = DateTimeExpiry(expiry) if not isinstance(expiry, DateTimeExpiry) else expiry
        except (  # policy_guard: allow-silent-handler
            TypeError,
            ValueError,
            ValidationError,
        ):
            continue
        if candidate == target:
            matches.append(expiry)
    return matches

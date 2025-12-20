"""Process dawn/dusk periods for chart shading."""

from datetime import datetime
from typing import List, Sequence, Tuple

import matplotlib.dates as mdates


def process_dawn_dusk_periods(
    dawn_dusk_periods: Sequence[Tuple[datetime, datetime]],
) -> Tuple[List[Tuple[float, datetime]], List[Tuple[float, datetime]]]:
    """
    Convert dawn/dusk datetime periods to matplotlib numeric format.

    Args:
        dawn_dusk_periods: Sequence of (dawn, dusk) datetime tuples

    Returns:
        Tuple of (all_dawns, all_dusks) sorted lists
    """
    all_dawns: List[Tuple[float, datetime]] = []
    all_dusks: List[Tuple[float, datetime]] = []

    for dawn, dusk in dawn_dusk_periods:
        dawn_naive = dawn.replace(tzinfo=None) if dawn.tzinfo else dawn
        dusk_naive = dusk.replace(tzinfo=None) if dusk.tzinfo else dusk
        all_dawns.append((float(mdates.date2num(dawn_naive)), dawn_naive))
        all_dusks.append((float(mdates.date2num(dusk_naive)), dusk_naive))

    all_dawns.sort(key=lambda entry: entry[0])
    all_dusks.sort(key=lambda entry: entry[0])

    return all_dawns, all_dusks

from __future__ import annotations

from typing import Any, Iterable

import numpy as np


def literal_array(values: Iterable[Any]) -> np.ndarray:
    return np.array(list(values))

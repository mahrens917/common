"""
Probability store package.

This package exposes a fail-fast API for storing and retrieving probability
payloads from Redis.
"""

from .exceptions import (
    ProbabilityDataNotFoundError,
    ProbabilityStoreError,
    ProbabilityStoreInitializationError,
    ProbabilityStoreVerificationError,
)
from .probability_data_config import ProbabilityData
from .store import ProbabilityStore
from .verification import (
    run_direct_connectivity_test,
    verify_probability_storage,
)

__all__ = [
    "ProbabilityStore",
    "ProbabilityData",
    "ProbabilityStoreError",
    "ProbabilityStoreInitializationError",
    "ProbabilityStoreVerificationError",
    "ProbabilityDataNotFoundError",
    "run_direct_connectivity_test",
    "verify_probability_storage",
]

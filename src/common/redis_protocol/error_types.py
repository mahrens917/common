"""
Shared exception groupings for Redis protocol modules.
"""

import asyncio
from json import JSONDecodeError
from typing import Tuple, Type

from redis.exceptions import RedisError

ExceptionTuple = Tuple[Type[BaseException], ...]

# Redis operations may surface redis-py errors along with generic timeout/OS failures.
REDIS_ERRORS: ExceptionTuple = (RedisError, asyncio.TimeoutError, OSError, RuntimeError)

# JSON helpers frequently coerce user-provided payloads.
JSON_ERRORS: ExceptionTuple = (TypeError, JSONDecodeError)

# Generic serialization helpers rely on stdlib coercion.
SERIALIZATION_ERRORS: ExceptionTuple = (TypeError, ValueError)

PARSING_ERRORS: ExceptionTuple = JSON_ERRORS + SERIALIZATION_ERRORS

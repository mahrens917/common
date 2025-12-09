"""Utilities for working with iterables and sequences."""

from typing import Iterable, List, Sequence, TypeVar

T = TypeVar("T")


def chunk(values: Sequence[T], chunk_size: int) -> Iterable[List[T]]:
    """
    Yield fixed-size chunks from a sequence.

    Args:
        values: Sequence to chunk
        chunk_size: Size of each chunk

    Yields:
        Lists of size chunk_size (last chunk may be smaller)

    Example:
        >>> list(chunk([1, 2, 3, 4, 5], 2))
        [[1, 2], [3, 4], [5]]
    """
    for index in range(0, len(values), chunk_size):
        yield list(values[index : index + chunk_size])


__all__ = ["chunk"]

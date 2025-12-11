"""Process lookup and search functionality."""

from typing import Dict, Iterable, List

from ..process_monitor import ProcessInfo


class ProcessLookup:
    """Handles process search and keyword matching."""

    @staticmethod
    def find_by_keywords(process_cache: Dict[int, ProcessInfo], keywords: Iterable[str]) -> List[ProcessInfo]:
        """
        Return processes whose command line contains any of the supplied keywords.

        Args:
            process_cache: Process cache to search
            keywords: Iterable of substrings to match against the process command line.

        Returns:
            A list of ProcessInfo entries matching the keywords.
        """
        normalized_keywords = [kw.lower() for kw in keywords if kw]
        if not normalized_keywords:
            return []

        matches: List[ProcessInfo] = []
        for process in process_cache.values():
            cmdline = " ".join(process.cmdline).lower()
            if any(keyword in cmdline for keyword in normalized_keywords):
                matches.append(process)

        return matches

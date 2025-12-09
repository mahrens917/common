"""Field iteration logic for probability ingestion."""

from typing import Any, Dict, Iterable, Tuple

from ..codec import serialize_probability_payload


class FieldIterator:
    """Handles iteration over probability fields."""

    def iter_probability_fields(
        self, probabilities_data: Dict[str, Dict[str, Dict[str, Any]]]
    ) -> Iterable[Tuple[str, str, bool, Dict[str, Any]]]:
        """
        Iterate over probability fields.

        Args:
            probabilities_data: Nested dict of expiry -> strike -> data

        Yields:
            Tuple of (field, serialized_value, has_confidence, original_data)
        """
        for expiry, strikes_data in probabilities_data.items():
            for strike, data in strikes_data.items():
                field = f"{expiry}:{strike}"
                serialized, has_confidence = serialize_probability_payload(data)
                yield field, serialized, has_confidence, data

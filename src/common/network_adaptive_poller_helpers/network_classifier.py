"""Network performance classification utilities."""

# Constants
_CONST_0_7 = 0.7
_CONST_0_85 = 0.85
_CONST_0_9 = 0.9
_CONST_10 = 10
_CONST_15 = 15
_CONST_30 = 30


class NetworkClassifier:
    """Classifies network type based on performance metrics."""

    @staticmethod
    def classify_network_type(avg_time: float, success_rate: float) -> str:
        """Classify network type based on performance metrics.

        Args:
            avg_time: Average request time in seconds
            success_rate: Success rate as decimal (0.0 to 1.0)

        Returns:
            Network type classification string
        """
        if avg_time < _CONST_10 and success_rate > _CONST_0_9:
            return "fast_reliable"  # AWS-like
        elif avg_time > _CONST_30 or success_rate < _CONST_0_7:
            return "slow_unreliable"  # Residential with issues
        elif avg_time > _CONST_15 or success_rate < _CONST_0_85:
            return "moderate"  # Decent residential
        else:
            return "good"  # Good residential or edge

import pytest

from common.simple_health_checker_helpers.activity_classifier import ActivityClassifier


class TestActivityClassifier:
    def test_init_defaults(self):
        classifier = ActivityClassifier()
        assert classifier.active_threshold_seconds == 3600
        assert classifier.fresh_threshold_seconds == 86400

    def test_init_custom(self):
        classifier = ActivityClassifier(active_threshold_seconds=10, fresh_threshold_seconds=20)
        assert classifier.active_threshold_seconds == 10
        assert classifier.fresh_threshold_seconds == 20

    def test_classify_active(self):
        classifier = ActivityClassifier(active_threshold_seconds=10, fresh_threshold_seconds=20)
        assert classifier.classify_log_activity(5) == "Active (5s old)"

    def test_classify_fresh(self):
        classifier = ActivityClassifier(active_threshold_seconds=10, fresh_threshold_seconds=20)
        assert classifier.classify_log_activity(15) == "Fresh (15s old)"

    def test_classify_stale(self):
        classifier = ActivityClassifier(active_threshold_seconds=10, fresh_threshold_seconds=20)
        assert classifier.classify_log_activity(25) == "Stale (25s old)"

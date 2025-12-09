from __future__ import annotations

"""Dependency factory for MarketLifecycleMonitor."""


from dataclasses import dataclass
from typing import Optional

from ..emergency_position_manager import EmergencyPositionManager
from ..kalshi_trading_client import KalshiTradingClient
from .close_detector import CloseDetector
from .expiry_checker import ExpiryChecker
from .lifecycle_orchestrator import LifecycleOrchestrator
from .market_registrar import MarketRegistrar
from .market_scanner import MarketScanner
from .notification_sender import NotificationSender
from .settlement_checker import SettlementChecker
from .settlement_fetcher import SettlementFetcher
from .settlement_validator import SettlementValidator
from .state_tracker import StateTracker


@dataclass(frozen=True)
class MarketLifecycleOptionalDeps:
    """Optional dependencies for MarketLifecycleMonitor."""

    scanner: Optional[MarketScanner] = None
    expiry_checker: Optional[ExpiryChecker] = None
    state_tracker: Optional[StateTracker] = None
    notifier: Optional[NotificationSender] = None
    close_detector: Optional[CloseDetector] = None
    settlement_fetcher: Optional[SettlementFetcher] = None
    settlement_checker: Optional[SettlementChecker] = None
    registrar: Optional[MarketRegistrar] = None
    settlement_validator: Optional[SettlementValidator] = None
    orchestrator: Optional[LifecycleOrchestrator] = None


def _all_deps_provided(optional: MarketLifecycleOptionalDeps) -> bool:
    """Check if all dependencies are provided."""
    return all(
        [
            optional.scanner,
            optional.expiry_checker,
            optional.state_tracker,
            optional.notifier,
            optional.close_detector,
            optional.settlement_fetcher,
            optional.settlement_checker,
            optional.registrar,
            optional.settlement_validator,
            optional.orchestrator,
        ]
    )


def _merge_field(optional_value, base_value):
    """Merge a single field, preferring optional over base.

    Note: Explicitly checks for None to avoid falsy-value substitution bugs.
    """
    if optional_value is not None:
        return optional_value
    return base_value


def _merge_deps(
    optional: MarketLifecycleOptionalDeps,
    defaults: MarketLifecycleMonitorDependencies,
) -> MarketLifecycleMonitorDependencies:
    """Merge provided deps with defaults."""
    return MarketLifecycleMonitorDependencies(  # gitleaks:allow
        scanner=_merge_field(optional.scanner, defaults.scanner),
        expiry_checker=_merge_field(optional.expiry_checker, defaults.expiry_checker),
        state_tracker=_merge_field(optional.state_tracker, defaults.state_tracker),
        notifier=_merge_field(optional.notifier, defaults.notifier),
        close_detector=_merge_field(optional.close_detector, defaults.close_detector),
        settlement_fetcher=_merge_field(optional.settlement_fetcher, defaults.settlement_fetcher),
        settlement_checker=_merge_field(optional.settlement_checker, defaults.settlement_checker),
        registrar=_merge_field(optional.registrar, defaults.registrar),
        settlement_validator=_merge_field(
            optional.settlement_validator, defaults.settlement_validator
        ),
        orchestrator=_merge_field(optional.orchestrator, defaults.orchestrator),
    )


@dataclass
class MarketLifecycleMonitorDependencies:
    """Container for all MarketLifecycleMonitor dependencies."""  # gitleaks:allow

    scanner: MarketScanner
    expiry_checker: ExpiryChecker
    state_tracker: StateTracker
    notifier: NotificationSender
    close_detector: CloseDetector
    settlement_fetcher: SettlementFetcher
    settlement_checker: SettlementChecker
    registrar: MarketRegistrar
    settlement_validator: SettlementValidator
    orchestrator: LifecycleOrchestrator


class MarketLifecycleMonitorDependenciesFactory:  # gitleaks:allow
    """Factory for creating MarketLifecycleMonitor dependencies."""

    @staticmethod
    def create(
        trading_client: KalshiTradingClient,
        emergency_manager: Optional[EmergencyPositionManager],
        closure_warning_hours: float,
    ) -> MarketLifecycleMonitorDependencies:  # gitleaks:allow
        """Create all dependencies for MarketLifecycleMonitor."""
        scanner = MarketScanner(trading_client)
        expiry_checker = ExpiryChecker(closure_warning_hours)
        state_tracker = StateTracker(scanner, expiry_checker)
        notifier = NotificationSender()
        close_detector = CloseDetector(trading_client, emergency_manager)
        settlement_fetcher = SettlementFetcher(scanner)
        settlement_checker = SettlementChecker(settlement_fetcher, state_tracker)

        registrar = MarketRegistrar(scanner, state_tracker, notifier)
        settlement_validator = SettlementValidator(state_tracker)
        orchestrator = LifecycleOrchestrator(
            state_tracker, close_detector, notifier, settlement_checker
        )

        return MarketLifecycleMonitorDependencies(  # gitleaks:allow
            scanner=scanner,
            expiry_checker=expiry_checker,
            state_tracker=state_tracker,
            notifier=notifier,
            close_detector=close_detector,
            settlement_fetcher=settlement_fetcher,
            settlement_checker=settlement_checker,
            registrar=registrar,
            settlement_validator=settlement_validator,
            orchestrator=orchestrator,
        )

    @staticmethod
    def create_or_use(
        trading_client: KalshiTradingClient,
        emergency_manager: Optional[EmergencyPositionManager],
        closure_warning_hours: float,
        optional: Optional[MarketLifecycleOptionalDeps] = None,
    ) -> MarketLifecycleMonitorDependencies:  # gitleaks:allow
        """Create dependencies only if not all are provided."""
        if optional is None:
            optional = MarketLifecycleOptionalDeps()

        if _all_deps_provided(optional):
            return MarketLifecycleMonitorDependencies(  # gitleaks:allow
                scanner=optional.scanner,  # type: ignore[arg-type]
                expiry_checker=optional.expiry_checker,  # type: ignore[arg-type]
                state_tracker=optional.state_tracker,  # type: ignore[arg-type]
                notifier=optional.notifier,  # type: ignore[arg-type]
                close_detector=optional.close_detector,  # type: ignore[arg-type]
                settlement_fetcher=optional.settlement_fetcher,  # type: ignore[arg-type]
                settlement_checker=optional.settlement_checker,  # type: ignore[arg-type]
                registrar=optional.registrar,  # type: ignore[arg-type]
                settlement_validator=optional.settlement_validator,  # type: ignore[arg-type]
                orchestrator=optional.orchestrator,  # type: ignore[arg-type]
            )

        defaults = MarketLifecycleMonitorDependenciesFactory.create(  # gitleaks:allow
            trading_client, emergency_manager, closure_warning_hours
        )
        return _merge_deps(optional, defaults)

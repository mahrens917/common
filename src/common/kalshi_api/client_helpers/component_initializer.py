"""Initialize KalshiClient components."""

from ..authentication import AuthenticationHelper
from ..order_operations import OrderOperations
from ..portfolio_operations import PortfolioOperations
from ..request_builder import RequestBuilder
from ..response_parser import ResponseParser
from ..session_manager import SessionManager


class ComponentInitializer:
    """Initialize all helper components for KalshiClient."""

    def __init__(self, config):
        """Initialize with config."""
        self.config = config

    def initialize(self, access_key: str, private_key):
        """Initialize all helper components."""
        session_manager = SessionManager(self.config)
        auth_helper = AuthenticationHelper(access_key, private_key)
        request_builder = RequestBuilder(
            self.config.base_url,
            session_manager,
            auth_helper,
            self.config.network_max_retries,
            self.config.network_backoff_base_seconds,
            self.config.network_backoff_max_seconds,
        )
        response_parser = ResponseParser()
        portfolio_ops = PortfolioOperations(request_builder)
        order_ops = OrderOperations(request_builder, response_parser)

        return {
            "session_manager": session_manager,
            "auth_helper": auth_helper,
            "request_builder": request_builder,
            "response_parser": response_parser,
            "portfolio_ops": portfolio_ops,
            "order_ops": order_ops,
        }

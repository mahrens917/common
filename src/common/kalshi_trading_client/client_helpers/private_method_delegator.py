"""Delegation layer for private method access."""


class PrivateMethodDelegator:
    """
    Provides controlled access to private methods through delegation.

    This class reduces boilerplate by consolidating all private method
    access patterns into a single delegation point.
    """

    def __init__(self, private_methods):
        """Initialize with private methods handler."""
        self._private = private_methods

    def build_order_poller(self):
        """Build order poller instance."""
        return self._private.build_order_poller()

    def build_trade_finalizer(self):
        """Build trade finalizer instance."""
        return self._private.build_trade_finalizer()

    def apply_polling_outcome(self, order_response, outcome):
        """Apply polling outcome to order response."""
        self._private.apply_polling_outcome(order_response, outcome)

    def validate_order_request(self, order_request):
        """Validate order request structure."""
        self._private.validate_order_request(order_request)

    def parse_order_response(self, response_data, operation_name, trade_rule, trade_reason):
        """Parse raw order response into OrderResponse."""
        return self._private.parse_order_response(
            response_data, operation_name, trade_rule, trade_reason
        )

    def has_sufficient_balance_for_trade_with_fees(
        self, cached_balance_cents, trade_cost_cents, fees_cents
    ):
        """Check if balance is sufficient for trade including fees."""
        return self._private.has_sufficient_balance_for_trade_with_fees(
            cached_balance_cents, trade_cost_cents, fees_cents
        )

    def create_icao_to_city_mapping(self):
        """Create ICAO code to city name mapping."""
        return self._private.create_icao_to_city_mapping()

    def extract_weather_station_from_ticker(self, market_ticker):
        """Extract weather station code from market ticker."""
        return self._private.extract_weather_station_from_ticker(market_ticker)

    def resolve_trade_context(self, market_ticker):
        """Resolve full trade context from market ticker."""
        return self._private.resolve_trade_context(market_ticker)

    async def calculate_order_fees(self, market_ticker, quantity, price_cents):
        """Calculate expected order fees."""
        return await self._private.calculate_order_fees(market_ticker, quantity, price_cents)

    async def get_trade_metadata_from_order(self, order_id):
        """Retrieve trade metadata for order."""
        return await self._private.get_trade_metadata_from_order(order_id)

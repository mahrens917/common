"""Service provider factory for InitializationCoordinator."""

from ..trade_store_ops import TradeStoreOperations


def create_service_providers(trade_store_manager, services_holder: dict) -> dict:
    """Create service provider functions."""

    def get_trade_store():
        return TradeStoreOperations.get_trade_store(trade_store_manager)

    def get_order_poller():
        private_methods = services_holder.get("private_methods")
        return private_methods.create_order_poller() if private_methods else None

    def get_trade_finalizer():
        private_methods = services_holder.get("private_methods")
        return private_methods.create_trade_finalizer() if private_methods else None

    return {
        "get_trade_store": get_trade_store,
        "get_order_poller": get_order_poller,
        "get_trade_finalizer": get_trade_finalizer,
    }

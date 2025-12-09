"""Helper modules for KalshiTradingClient slim coordinator."""

from .attribute_handler import AttributeHandler
from .attribute_resolver import ClientAttributeResolver
from .factory_methods import FactoryMethods
from .initialization import ClientInitializer
from .lifecycle import LifecycleManager
from .order_operations import OrderOperations
from .order_polling_override_handler import OrderPollingOverrideHandler
from .portfolio_operations import PortfolioOperations
from .private_method_delegator import PrivateMethodDelegator
from .private_methods import PrivateMethods
from .protocols import (
    IAttributeResolver,
    ILifecycleManager,
    IOrderPollingHandler,
    IOrderService,
    IPortfolioService,
    IPrivateMethods,
    IPublicAPI,
    ITradeCollectionService,
    ITradeContextResolver,
    ITradeStoreOperations,
)
from .public_api import PublicAPI
from .public_api_delegator import PublicAPIDelegator
from .trade_collection import TradeCollectionManager
from .trade_context import TradeContextResolver
from .trade_store_ops import TradeStoreOperations

__all__ = [
    "AttributeHandler",
    "ClientAttributeResolver",
    "ClientInitializer",
    "FactoryMethods",
    "LifecycleManager",
    "OrderOperations",
    "OrderPollingOverrideHandler",
    "PortfolioOperations",
    "PrivateMethodDelegator",
    "PrivateMethods",
    "PublicAPI",
    "PublicAPIDelegator",
    "TradeCollectionManager",
    "TradeContextResolver",
    "TradeStoreOperations",
    # Protocols
    "IAttributeResolver",
    "ILifecycleManager",
    "IOrderPollingHandler",
    "IOrderService",
    "IPortfolioService",
    "IPrivateMethods",
    "IPublicAPI",
    "ITradeCollectionService",
    "ITradeContextResolver",
    "ITradeStoreOperations",
]

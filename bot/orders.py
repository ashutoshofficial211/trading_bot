"""Business logic for placing Futures orders."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import logging
from typing import Any, Optional

from .client import BinanceClientError, BinanceFuturesTestnetClient
from .validators import (
    OrderRequest,
    ValidationError,
    format_decimal,
    validate_symbol_trading_rules,
)


class OrderPlacementError(RuntimeError):
    """Raised when an order cannot be submitted successfully."""


@dataclass(frozen=True, slots=True)
class OrderResult:
    """Container for a validated order request and Binance API response."""

    request: OrderRequest
    response: dict[str, Any]

    @property
    def order_id(self) -> str:
        """Return the Binance order identifier from the response."""
        return str(self.response.get("orderId", "N/A"))

    @property
    def status(self) -> str:
        """Return the Binance order status from the response."""
        return str(self.response.get("status", "UNKNOWN"))

    @property
    def executed_quantity(self) -> str:
        """Return the executed quantity from the response."""
        value = self.response.get("executedQty", self.response.get("origQty", "0"))
        return str(value)

    @property
    def average_price(self) -> Optional[str]:
        """Return the average execution price when Binance provides enough data."""
        avg_price = self.response.get("avgPrice")
        if is_positive_decimal(avg_price):
            return str(avg_price)

        executed_quantity = self.response.get("executedQty")
        cum_quote = self.response.get("cumQuote")
        if not is_positive_decimal(executed_quantity) or not is_positive_decimal(
            cum_quote
        ):
            return None

        quantity_decimal = Decimal(str(executed_quantity))
        quote_decimal = Decimal(str(cum_quote))
        if quantity_decimal == 0:
            return None

        return format_decimal(quote_decimal / quantity_decimal)


class OrderService:
    """Service that validates trading rules before placing orders."""

    def __init__(self, client: BinanceFuturesTestnetClient) -> None:
        """Create an order service backed by a Binance client wrapper."""
        self._client = client
        self._logger = logging.getLogger(__name__)

    def place_order(self, order_request: OrderRequest) -> OrderResult:
        """Validate symbol rules and submit an order to Binance Demo Trading."""
        symbol_info = self._client.get_symbol_info(order_request.symbol)
        if symbol_info is None:
            raise OrderPlacementError(
                f"Symbol {order_request.symbol} is not available on Binance Futures Demo Trading."
            )

        try:
            validate_symbol_trading_rules(order_request, symbol_info)
        except ValidationError as exc:
            self._logger.exception(
                "Order validation against Binance symbol rules failed for %s.",
                order_request.symbol,
            )
            raise OrderPlacementError(str(exc)) from exc

        try:
            response = self._client.place_order(order_request)
        except BinanceClientError as exc:
            raise OrderPlacementError(str(exc)) from exc

        return OrderResult(request=order_request, response=response)


def is_positive_decimal(value: Any) -> bool:
    """Return True when a value can be parsed as a positive Decimal."""
    if value in (None, ""):
        return False

    try:
        return Decimal(str(value)) > 0
    except (InvalidOperation, TypeError, ValueError):
        return False

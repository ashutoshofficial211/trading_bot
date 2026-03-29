"""Validation helpers for CLI inputs and Binance symbol rules."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_CEILING
import re
from typing import Any, Mapping, Optional

VALID_ORDER_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT"}
SYMBOL_PATTERN = re.compile(r"^[A-Z0-9]{5,20}$")


class ValidationError(ValueError):
    """Raised when user input or exchange constraints are invalid."""


@dataclass(frozen=True, slots=True)
class OrderRequest:
    """Validated order request data ready for business logic."""

    symbol: str
    side: str
    order_type: str
    quantity: Decimal
    price: Optional[Decimal] = None


@dataclass(frozen=True, slots=True)
class SymbolTradingRules:
    """Trading rules derived from Binance Futures exchange metadata."""

    symbol: str
    status: str
    min_quantity: Decimal
    max_quantity: Decimal
    quantity_step: Decimal
    min_price: Optional[Decimal]
    max_price: Optional[Decimal]
    price_tick_size: Optional[Decimal]
    min_notional: Optional[Decimal]
    max_notional: Optional[Decimal]


def build_order_request(
    symbol: str,
    side: str,
    order_type: str,
    quantity: str,
    price: Optional[str],
) -> OrderRequest:
    """Validate raw CLI inputs and return a normalized order request."""
    normalized_symbol = validate_symbol(symbol)
    normalized_side = validate_side(side)
    normalized_order_type = validate_order_type(order_type)
    normalized_quantity = parse_positive_decimal(quantity, field_name="quantity")
    normalized_price = parse_price(price, order_type=normalized_order_type)

    return OrderRequest(
        symbol=normalized_symbol,
        side=normalized_side,
        order_type=normalized_order_type,
        quantity=normalized_quantity,
        price=normalized_price,
    )


def validate_symbol(symbol: str) -> str:
    """Validate and normalize the symbol."""
    normalized_symbol = str(symbol).strip().upper()
    if not normalized_symbol:
        raise ValidationError("Symbol is required.")
    if not SYMBOL_PATTERN.fullmatch(normalized_symbol):
        raise ValidationError(
            "Symbol must contain only letters and numbers, for example BTCUSDT."
        )
    return normalized_symbol


def validate_side(side: str) -> str:
    """Validate and normalize the order side."""
    normalized_side = str(side).strip().upper()
    if normalized_side not in VALID_ORDER_SIDES:
        raise ValidationError("Side must be either BUY or SELL.")
    return normalized_side


def validate_order_type(order_type: str) -> str:
    """Validate and normalize the order type."""
    normalized_order_type = str(order_type).strip().upper()
    if normalized_order_type not in VALID_ORDER_TYPES:
        raise ValidationError("Type must be either MARKET or LIMIT.")
    return normalized_order_type


def parse_positive_decimal(value: str, field_name: str) -> Decimal:
    """Parse a positive decimal string into a Decimal instance."""
    raw_value = str(value).strip()
    if not raw_value:
        raise ValidationError(f"{field_name.capitalize()} is required.")

    try:
        decimal_value = Decimal(raw_value)
    except InvalidOperation as exc:
        raise ValidationError(
            f"{field_name.capitalize()} must be a valid number."
        ) from exc

    if decimal_value <= 0:
        raise ValidationError(f"{field_name.capitalize()} must be greater than zero.")
    return decimal_value


def parse_price(price: Optional[str], order_type: str) -> Optional[Decimal]:
    """Validate price rules based on order type and return a Decimal when present."""
    has_price = price is not None and str(price).strip() != ""

    if order_type == "LIMIT" and not has_price:
        raise ValidationError("Price is required for LIMIT orders.")
    if order_type == "MARKET" and has_price:
        raise ValidationError("Price must not be provided for MARKET orders.")
    if not has_price:
        return None

    return parse_positive_decimal(str(price), field_name="price")


def validate_symbol_trading_rules(
    order_request: OrderRequest, symbol_info: Mapping[str, Any]
) -> None:
    """Validate quantity and price against Binance symbol exchange rules."""
    trading_rules = extract_symbol_trading_rules(
        symbol_info=symbol_info,
        order_type=order_request.order_type,
    )

    if trading_rules.symbol != order_request.symbol:
        raise ValidationError(
            f"Exchange metadata mismatch for symbol {order_request.symbol}."
        )
    if trading_rules.status != "TRADING":
        raise ValidationError(
            f"Symbol {order_request.symbol} is not currently tradable on Binance Futures Demo Trading."
        )

    validate_range(
        value=order_request.quantity,
        minimum=trading_rules.min_quantity,
        maximum=trading_rules.max_quantity,
        field_name="quantity",
    )
    validate_step_size(
        value=order_request.quantity,
        step_size=trading_rules.quantity_step,
        field_name="quantity",
    )

    if order_request.order_type == "LIMIT":
        if order_request.price is None:
            raise ValidationError("Price is required for LIMIT orders.")
        if trading_rules.min_price is None or trading_rules.max_price is None:
            raise ValidationError(
                f"Binance did not provide a usable price filter for {order_request.symbol}."
            )

        validate_range(
            value=order_request.price,
            minimum=trading_rules.min_price,
            maximum=trading_rules.max_price,
            field_name="price",
        )
        validate_step_size(
            value=order_request.price,
            step_size=trading_rules.price_tick_size,
            field_name="price",
        )
        validate_notional(
            quantity=order_request.quantity,
            price=order_request.price,
            trading_rules=trading_rules,
        )


def extract_symbol_trading_rules(
    symbol_info: Mapping[str, Any], order_type: str
) -> SymbolTradingRules:
    """Extract symbol trading rules from Binance exchange metadata."""
    filters = {
        str(item.get("filterType")): item for item in symbol_info.get("filters", [])
    }

    quantity_filter_name = (
        "MARKET_LOT_SIZE"
        if order_type == "MARKET" and "MARKET_LOT_SIZE" in filters
        else "LOT_SIZE"
    )
    quantity_filter = filters.get(quantity_filter_name)
    if quantity_filter is None:
        raise ValidationError(
            f"Binance did not return a {quantity_filter_name} filter for {symbol_info.get('symbol', 'UNKNOWN')}."
        )

    price_filter = filters.get("PRICE_FILTER")
    notional_filter = filters.get("NOTIONAL") or filters.get("MIN_NOTIONAL")

    return SymbolTradingRules(
        symbol=str(symbol_info.get("symbol", "")).upper(),
        status=str(symbol_info.get("status", "UNKNOWN")).upper(),
        min_quantity=parse_filter_decimal(quantity_filter, "minQty"),
        max_quantity=parse_filter_decimal(quantity_filter, "maxQty"),
        quantity_step=parse_filter_decimal(quantity_filter, "stepSize"),
        min_price=parse_optional_filter_decimal(price_filter, "minPrice"),
        max_price=parse_optional_filter_decimal(price_filter, "maxPrice"),
        price_tick_size=parse_optional_filter_decimal(price_filter, "tickSize"),
        min_notional=parse_first_available_filter_decimal(
            notional_filter,
            "minNotional",
            "notional",
        ),
        max_notional=parse_first_available_filter_decimal(
            notional_filter,
            "maxNotional",
        ),
    )


def parse_filter_decimal(filter_data: Mapping[str, Any], field_name: str) -> Decimal:
    """Parse a required decimal field from a Binance symbol filter."""
    value = parse_optional_filter_decimal(filter_data, field_name)
    if value is None:
        raise ValidationError(
            f"Binance did not return the required filter field {field_name}."
        )
    return value


def parse_optional_filter_decimal(
    filter_data: Optional[Mapping[str, Any]], field_name: str
) -> Optional[Decimal]:
    """Parse an optional decimal field from a Binance symbol filter."""
    if filter_data is None:
        return None

    raw_value = filter_data.get(field_name)
    if raw_value in (None, ""):
        return None

    try:
        return Decimal(str(raw_value))
    except InvalidOperation as exc:
        raise ValidationError(
            f"Binance returned an invalid decimal value for {field_name}: {raw_value}"
        ) from exc


def parse_first_available_filter_decimal(
    filter_data: Optional[Mapping[str, Any]], *field_names: str
) -> Optional[Decimal]:
    """Parse the first available decimal value from a list of filter field names."""
    for field_name in field_names:
        value = parse_optional_filter_decimal(filter_data, field_name)
        if value is not None:
            return value
    return None


def validate_range(
    value: Decimal, minimum: Decimal, maximum: Decimal, field_name: str
) -> None:
    """Validate that a Decimal value is within an inclusive range."""
    if minimum > 0 and value < minimum:
        raise ValidationError(
            f"{field_name.capitalize()} must be at least {format_decimal(minimum)}."
        )
    if maximum > 0 and value > maximum:
        raise ValidationError(
            f"{field_name.capitalize()} must not exceed {format_decimal(maximum)}."
        )


def validate_step_size(
    value: Decimal, step_size: Optional[Decimal], field_name: str
) -> None:
    """Validate that a Decimal value aligns to the provided Binance step size."""
    if step_size is None or step_size == 0:
        return

    if value % step_size != 0:
        raise ValidationError(
            f"{field_name.capitalize()} must align with Binance step size {format_decimal(step_size)}."
        )


def validate_notional(
    quantity: Decimal,
    price: Decimal,
    trading_rules: SymbolTradingRules,
) -> None:
    """Validate order notional against Binance minimum and maximum notional rules."""
    notional = quantity * price

    if trading_rules.min_notional and trading_rules.min_notional > 0:
        if notional < trading_rules.min_notional:
            minimum_quantity = calculate_minimum_quantity_for_notional(
                minimum_notional=trading_rules.min_notional,
                price=price,
                quantity_step=trading_rules.quantity_step,
            )
            raise ValidationError(
                "Order notional is too small. "
                f"Binance requires at least {format_decimal(trading_rules.min_notional)} USDT, "
                f"but this order totals {format_decimal(notional)} USDT. "
                f"At price {format_decimal(price)}, quantity must be at least {format_decimal(minimum_quantity)}."
            )

    if trading_rules.max_notional and trading_rules.max_notional > 0:
        if notional > trading_rules.max_notional:
            raise ValidationError(
                "Order notional is too large. "
                f"Binance allows at most {format_decimal(trading_rules.max_notional)} USDT for this symbol/filter."
            )


def calculate_minimum_quantity_for_notional(
    minimum_notional: Decimal,
    price: Decimal,
    quantity_step: Decimal,
) -> Decimal:
    """Return the smallest quantity that satisfies a minimum notional constraint."""
    required_quantity = minimum_notional / price
    if quantity_step <= 0:
        return required_quantity

    return (
        (required_quantity / quantity_step).to_integral_value(rounding=ROUND_CEILING)
        * quantity_step
    )


def format_decimal(value: Decimal) -> str:
    """Convert a Decimal to a plain string without scientific notation."""
    normalized_value = format(value, "f")
    if "." in normalized_value:
        normalized_value = normalized_value.rstrip("0").rstrip(".")
    return normalized_value

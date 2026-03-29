"""Presentation helpers shared by the CLI and web UI."""

from __future__ import annotations

from dataclasses import dataclass

from .orders import OrderResult
from .validators import OrderRequest, format_decimal


@dataclass(frozen=True, slots=True)
class SummaryField:
    """Display-ready label and value pair for user-facing summaries."""

    label: str
    value: str


def build_request_summary(order_request: OrderRequest) -> list[SummaryField]:
    """Return a display-friendly summary of an order request."""
    fields = [
        SummaryField(label="Symbol", value=order_request.symbol),
        SummaryField(label="Side", value=order_request.side),
        SummaryField(label="Type", value=order_request.order_type),
        SummaryField(label="Quantity", value=format_decimal(order_request.quantity)),
    ]

    if order_request.price is not None:
        fields.append(
            SummaryField(label="Price", value=format_decimal(order_request.price))
        )

    return fields


def build_response_summary(result: OrderResult) -> list[SummaryField]:
    """Return a display-friendly summary of a Binance order response."""
    fields = [
        SummaryField(label="orderId", value=result.order_id),
        SummaryField(label="status", value=result.status),
        SummaryField(label="executedQty", value=result.executed_quantity),
    ]

    if result.average_price is not None:
        fields.append(SummaryField(label="avgPrice", value=result.average_price))

    return fields

"""Typer CLI entry point for the Binance Futures Demo Trading bot."""

from __future__ import annotations

from typing import Optional

import typer

from bot.client import BinanceFuturesTestnetClient, MissingCredentialsError
from bot.logging_config import setup_logging
from bot.orders import OrderPlacementError, OrderResult, OrderService
from bot.presenters import build_request_summary, build_response_summary
from bot.validators import OrderRequest, ValidationError, build_order_request

app = typer.Typer(
    add_completion=False,
    help="Place USDT-M Futures orders on Binance Futures Demo Trading.",
)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Initialize application-wide logging before commands run."""
    setup_logging()
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        typer.echo("Example:")
        typer.echo(
            "python cli.py place-order --symbol BTCUSDT --side BUY --type LIMIT --quantity 0.001 --price 50000"
        )
        raise typer.Exit(code=0)


@app.command("place-order")
def place_order(
    symbol: str = typer.Option(
        ...,
        "--symbol",
        help="Futures trading symbol, for example BTCUSDT.",
    ),
    side: str = typer.Option(
        ...,
        "--side",
        help="Order side: BUY or SELL.",
    ),
    order_type: str = typer.Option(
        ...,
        "--type",
        help="Order type: MARKET or LIMIT.",
    ),
    quantity: str = typer.Option(
        ...,
        "--quantity",
        help="Order quantity as a positive decimal.",
    ),
    price: Optional[str] = typer.Option(
        None,
        "--price",
        help="Limit price. Required for LIMIT orders and forbidden for MARKET orders.",
    ),
) -> None:
    """Place a MARKET or LIMIT order on Binance Futures Demo Trading."""
    try:
        order_request = build_order_request(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
        )
    except ValidationError as exc:
        exit_with_failure(f"Input validation error: {exc}")

    print_order_request_summary(order_request)

    try:
        client = BinanceFuturesTestnetClient()
        service = OrderService(client=client)
        result = service.place_order(order_request)
    except MissingCredentialsError as exc:
        exit_with_failure(str(exc))
    except OrderPlacementError as exc:
        exit_with_failure(str(exc))

    print_order_response(result)
    print_success_status()


def print_order_request_summary(order_request: OrderRequest) -> None:
    """Print a structured summary of the order request."""
    typer.echo("Order Request Summary:")
    for field in build_request_summary(order_request):
        typer.echo(f"- {field.label}: {field.value}")


def print_order_response(result: OrderResult) -> None:
    """Print a structured summary of the Binance order response."""
    typer.echo("")
    typer.echo("Order Response:")
    for field in build_response_summary(result):
        typer.echo(f"- {field.label}: {field.value}")


def print_success_status() -> None:
    """Print a successful command status block."""
    typer.echo("")
    typer.echo("Final Status:")
    typer.echo("- SUCCESS")


def exit_with_failure(message: str) -> None:
    """Print a clean failure message and terminate the command."""
    typer.secho(f"Error: {message}", fg=typer.colors.RED, err=True)
    typer.echo("")
    typer.echo("Final Status:")
    typer.echo("- FAILED")
    raise typer.Exit(code=1)


if __name__ == "__main__":
    app()

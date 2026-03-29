"""Binance Futures Demo Trading client wrapper."""

from __future__ import annotations

import logging
import os
from decimal import Decimal
from pathlib import Path
import re
import time
from typing import Any, Optional

from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException
from dotenv import load_dotenv
from requests.exceptions import RequestException

from .validators import OrderRequest, format_decimal


class BinanceClientError(RuntimeError):
    """Raised when Binance client operations fail."""


class MissingCredentialsError(BinanceClientError):
    """Raised when required Binance API credentials are missing."""


class BinanceFuturesTestnetClient:
    """Wrapper around python-binance for USDT-M Futures Demo Trading operations."""

    BASE_URL = "https://demo-fapi.binance.com"
    REQUEST_TIMEOUT_SECONDS = 10
    TIME_SYNC_TTL_SECONDS = 60
    ENV_FILE_NAME = ".env"

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
    ) -> None:
        """Initialize the Binance Futures Demo Trading client."""
        env_file_path = Path(__file__).resolve().parents[1] / self.ENV_FILE_NAME
        load_dotenv(dotenv_path=env_file_path, override=True)
        load_dotenv(override=True)

        resolved_api_key = api_key or os.getenv("BINANCE_API_KEY")
        resolved_api_secret = api_secret or os.getenv("BINANCE_API_SECRET")

        if not resolved_api_key or not resolved_api_secret:
            raise MissingCredentialsError(
                "Missing Binance API credentials. Set BINANCE_API_KEY and BINANCE_API_SECRET."
            )

        self._logger = logging.getLogger(__name__)
        self._exchange_info_cache: Optional[dict[str, Any]] = None
        self._last_time_sync_epoch_seconds = 0.0
        self._client = Client(
            api_key=resolved_api_key,
            api_secret=resolved_api_secret,
            demo=True,
            requests_params={"timeout": self.REQUEST_TIMEOUT_SECONDS},
        )

        self._logger.debug(
            "Initialized Binance Futures Demo Trading client. base_url=%s futures_api_base=%s",
            self.BASE_URL,
            self._client._create_futures_api_uri("ping"),
        )
        self._sync_time_offset(force=True)

    def get_exchange_info(self, force_refresh: bool = False) -> dict[str, Any]:
        """Return Futures exchange info, using an in-memory cache by default."""
        if self._exchange_info_cache is not None and not force_refresh:
            self._logger.debug("Using cached futures exchange info.")
            return self._exchange_info_cache

        try:
            self._logger.debug("API request: futures_exchange_info")
            response = self._client.futures_exchange_info()
            self._logger.debug(
                "API response: futures_exchange_info symbol_count=%s timezone=%s",
                len(response.get("symbols", [])),
                response.get("timezone"),
            )
            self._exchange_info_cache = response
            return response
        except (BinanceAPIException, BinanceRequestException, RequestException) as exc:
            self._raise_client_error("fetching Futures exchange info", exc)

    def get_symbol_info(self, symbol: str) -> Optional[dict[str, Any]]:
        """Return symbol metadata for a Futures instrument if it exists."""
        exchange_info = self.get_exchange_info()

        for symbol_info in exchange_info.get("symbols", []):
            if str(symbol_info.get("symbol", "")).upper() == symbol.upper():
                self._logger.debug(
                    "Resolved symbol info for %s with status=%s",
                    symbol,
                    symbol_info.get("status"),
                )
                return symbol_info

        self._logger.debug(
            "Symbol %s was not found in Binance Futures exchange info.", symbol
        )
        return None

    def place_order(self, order_request: OrderRequest) -> dict[str, Any]:
        """Place a Futures order on Binance Demo Trading and return the API response."""
        payload = self.build_order_payload(order_request)
        self._ensure_time_offset_is_fresh()

        try:
            response = self._submit_order_request(payload)
            self._logger.debug("API response: futures_create_order response=%s", response)
            return response
        except BinanceAPIException as exc:
            if str(exc.code) == "-1021":
                self._logger.warning(
                    "Binance rejected the request timestamp. Refreshing server time and retrying once."
                )
                self._sync_time_offset(force=True)
                try:
                    response = self._submit_order_request(payload)
                    self._logger.debug(
                        "API response after time resync: futures_create_order response=%s",
                        response,
                    )
                    return response
                except (
                    BinanceAPIException,
                    BinanceRequestException,
                    RequestException,
                ) as retry_exc:
                    self._raise_client_error("placing a Futures order", retry_exc)

            if (
                str(exc.code) == "-4164"
                or "no smaller than" in str(exc.message).lower()
            ):
                self._raise_min_notional_error(exc=exc, order_request=order_request)

            self._raise_client_error("placing a Futures order", exc)
        except (BinanceRequestException, RequestException) as exc:
            self._raise_client_error("placing a Futures order", exc)

    def build_order_payload(self, order_request: OrderRequest) -> dict[str, str]:
        """Build a Binance Futures order payload from a validated order request."""
        payload = {
            "symbol": order_request.symbol,
            "side": order_request.side,
            "type": order_request.order_type,
            "quantity": format_decimal(order_request.quantity),
            "newOrderRespType": "RESULT",
        }

        if order_request.order_type == "LIMIT":
            payload["timeInForce"] = "GTC"
            payload["price"] = format_decimal(order_request.price)  # type: ignore[arg-type]

        return payload

    def _submit_order_request(self, payload: dict[str, str]) -> dict[str, Any]:
        """Submit a signed Futures order request to Binance."""
        self._logger.debug("API request: futures_create_order payload=%s", payload)
        return self._client.futures_create_order(**payload)

    def _ensure_time_offset_is_fresh(self) -> None:
        """Refresh Binance server time offset when the cached value is stale."""
        if (
            time.time() - self._last_time_sync_epoch_seconds
            >= self.TIME_SYNC_TTL_SECONDS
        ):
            self._sync_time_offset(force=True)

    def _sync_time_offset(self, force: bool = False) -> None:
        """Sync local request timestamps against Binance server time."""
        if not force and (
            time.time() - self._last_time_sync_epoch_seconds < self.TIME_SYNC_TTL_SECONDS
        ):
            return

        try:
            self._logger.debug("API request: futures_time")
            response = self._client.futures_time()
            server_time = int(response["serverTime"])
            local_time = int(time.time() * 1000)
            self._client.timestamp_offset = server_time - local_time
            self._last_time_sync_epoch_seconds = time.time()
            self._logger.debug(
                "API response: futures_time server_time=%s local_time=%s timestamp_offset=%s",
                server_time,
                local_time,
                self._client.timestamp_offset,
            )
        except (BinanceAPIException, BinanceRequestException, RequestException) as exc:
            self._logger.warning(
                "Failed to sync Binance server time before a signed request: %s",
                exc,
            )

    def _raise_client_error(self, action: str, exc: Exception) -> None:
        """Log a client failure and raise a normalized application error."""
        if isinstance(exc, BinanceAPIException):
            message = self._format_api_error_message(action=action, exc=exc)
        elif isinstance(exc, BinanceRequestException):
            message = f"Binance request error while {action}: {exc.message}"
        elif isinstance(exc, RequestException):
            message = f"Network error while {action}: {exc}"
        else:
            message = f"Unexpected error while {action}: {exc}"

        self._logger.exception(message)
        raise BinanceClientError(message) from exc

    def _raise_min_notional_error(
        self, exc: BinanceAPIException, order_request: OrderRequest
    ) -> None:
        """Raise a clearer minimum-notional error using the current order values."""
        if order_request.price is None:
            self._raise_client_error("placing a Futures order", exc)

        current_notional = order_request.quantity * order_request.price
        minimum_notional = extract_minimum_notional_from_message(exc.message)

        if minimum_notional is None:
            self._raise_client_error("placing a Futures order", exc)

        minimum_quantity = minimum_notional / order_request.price
        message = (
            "Order notional is too small. "
            f"This ticket totals {format_decimal(current_notional)} USDT, "
            f"but Binance requires at least {format_decimal(minimum_notional)} USDT. "
            f"At price {format_decimal(order_request.price)}, quantity must be at least {format_decimal(minimum_quantity)}."
        )
        self._logger.exception(message)
        raise BinanceClientError(message) from exc

    def _format_api_error_message(
        self, action: str, exc: BinanceAPIException
    ) -> str:
        """Return a user-friendly Binance API error message with targeted hints."""
        message = f"Binance API error while {action}: [{exc.code}] {exc.message}"
        error_code = str(exc.code)
        error_message = str(exc.message).lower()

        if error_code == "-2014":
            return (
                f"{message} "
                "Use a Binance Demo Trading Futures HMAC API key from "
                "https://demo.binance.com/en/my/settings/api-management, "
                "and make sure BINANCE_API_KEY contains the API Key while "
                "BINANCE_API_SECRET contains the Secret Key."
            )

        if error_code == "-2015":
            return (
                f"{message} "
                "Check that the Demo Trading key is active and has the required Futures permissions."
            )

        if error_code == "-1022":
            return (
                f"{message} "
                "The signature did not match. Re-copy the Secret Key and confirm the key/secret pair belongs together."
            )

        if error_code == "-1021":
            return (
                f"{message} "
                "Your local clock appears out of sync with Binance. The client retried after refreshing server time; "
                "if this keeps happening, sync your system clock and try again."
            )

        if error_code == "-4164" or "no smaller than" in error_message:
            return (
                f"{message} "
                "Increase the order quantity or price so the order notional clears Binance's minimum threshold."
            )

        if error_code == "0" and "restricted location" in error_message:
            return (
                f"{message} "
                "Binance rejected the request based on the backend server location. "
                "If this app is running on Vercel, move the Function region out of the default US region "
                "and redeploy. If the error still appears after that, Binance is likely blocking the hosting "
                "provider's egress IP, so the trading backend will need to run from a different server or your local machine."
            )

        return message


def extract_minimum_notional_from_message(message: str) -> Optional[Decimal]:
    """Extract the minimum notional amount from a Binance error message when present."""
    match = re.search(r"no smaller than\s+(\d+(?:\.\d+)?)", message)
    if match is None:
        return None

    return Decimal(match.group(1))

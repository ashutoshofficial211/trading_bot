"""FastAPI web UI for Binance Futures Demo Trading order placement."""

from __future__ import annotations

from contextlib import asynccontextmanager
import logging
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
from pydantic import BaseModel, ConfigDict, Field
import uvicorn

from bot.client import BinanceFuturesTestnetClient, MissingCredentialsError
from bot.logging_config import get_log_file_path, is_vercel_runtime, setup_logging
from bot.orders import OrderPlacementError, OrderResult, OrderService
from bot.presenters import SummaryField, build_request_summary, build_response_summary
from bot.validators import ValidationError, build_order_request

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
PUBLIC_DIR = BASE_DIR / "public"
ASSETS_DIR = PUBLIC_DIR / "assets"

logger = logging.getLogger(__name__)
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


class OrderSubmissionPayload(BaseModel):
    """JSON payload accepted by the web UI order endpoint."""

    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    symbol: str
    side: str
    order_type: str = Field(alias="orderType")
    quantity: str
    price: Optional[str] = None


class SummaryFieldPayload(BaseModel):
    """Serialized summary field returned to the browser."""

    label: str
    value: str


class OrderSubmissionResponse(BaseModel):
    """Structured order submission result returned to the browser."""

    final_status: Literal["SUCCESS", "FAILED"] = Field(alias="finalStatus")
    request_summary: list[SummaryFieldPayload] = Field(alias="requestSummary")
    order_response: list[SummaryFieldPayload] = Field(
        default_factory=list, alias="orderResponse"
    )
    error_message: Optional[str] = Field(default=None, alias="errorMessage")


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Configure logging once when the web application starts."""
    log_file_path = setup_logging()
    logger.debug("Starting Binance Futures Demo Trading web UI. log_file=%s", log_file_path)
    yield
    logger.debug("Stopping Binance Futures Demo Trading web UI.")


app = FastAPI(
    title="Binance Futures Demo Trading UI",
    description="Local browser UI for placing USDT-M Futures Demo Trading orders.",
    version="0.2.0",
    lifespan=lifespan,
)
if not is_vercel_runtime():
    app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """Render the main trading form UI."""
    context = {
        "request": request,
        "log_file_path": str(get_log_file_path()),
        "binance_base_url": BinanceFuturesTestnetClient.BASE_URL,
    }
    return templates.TemplateResponse(request, "index.html", context)


@app.post("/api/orders", response_model=OrderSubmissionResponse)
async def submit_order(
    payload: OrderSubmissionPayload,
) -> OrderSubmissionResponse:
    """Validate and submit an order request from the browser UI."""
    logger.debug(
        "Web UI order submission received. symbol=%s side=%s order_type=%s",
        payload.symbol,
        payload.side,
        payload.order_type,
    )

    try:
        order_request = build_order_request(
            symbol=payload.symbol,
            side=payload.side,
            order_type=payload.order_type,
            quantity=payload.quantity,
            price=payload.price,
        )
    except ValidationError as exc:
        logger.exception("Web UI validation failed before order submission.")
        return build_failure_response(
            message=f"Input validation error: {exc}",
            request_summary=[],
        )

    request_summary = build_request_summary(order_request)

    try:
        service = OrderService(client=BinanceFuturesTestnetClient())
        result = service.place_order(order_request)
    except MissingCredentialsError as exc:
        logger.exception("Web UI submission failed because credentials are missing.")
        return build_failure_response(
            message=str(exc),
            request_summary=request_summary,
        )
    except OrderPlacementError as exc:
        logger.exception("Web UI submission failed during order placement.")
        return build_failure_response(
            message=str(exc),
            request_summary=request_summary,
        )
    except Exception as exc:
        logger.exception("Web UI submission failed because of an unexpected backend error.")
        return build_failure_response(
            message=(
                "The Python backend hit an unexpected error while processing this order. "
                f"Details: {exc}"
            ),
            request_summary=request_summary,
        )

    return OrderSubmissionResponse(
        finalStatus="SUCCESS",
        requestSummary=serialize_summary_fields(request_summary),
        orderResponse=serialize_summary_fields(build_response_summary(result)),
    )


def build_failure_response(
    message: str, request_summary: list[SummaryField]
) -> OrderSubmissionResponse:
    """Build a consistent failed order submission response."""
    return OrderSubmissionResponse(
        finalStatus="FAILED",
        requestSummary=serialize_summary_fields(request_summary),
        errorMessage=message,
    )


def serialize_summary_fields(fields: list[SummaryField]) -> list[SummaryFieldPayload]:
    """Convert summary dataclasses into JSON response models."""
    return [SummaryFieldPayload(label=field.label, value=field.value) for field in fields]


if __name__ == "__main__":
    uvicorn.run("web:app", host="127.0.0.1", port=8000, reload=False)

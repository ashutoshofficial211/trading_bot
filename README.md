# Binance Futures Demo Trading App

Production-oriented Python application for placing USDT-M Futures orders on Binance Futures Demo Trading using `python-binance`.

## Overview

This project provides a small but structured command-line tool that:

- Places `MARKET` and `LIMIT` orders on Binance Futures Demo Trading
- Offers a local browser UI for order entry and execution feedback
- Loads credentials from environment variables
- Validates user input before submitting orders
- Validates order quantity and price against Binance exchange filters when possible
- Writes detailed DEBUG logs to `trading_bot.log`

The code is intentionally split so the UI and CLI stay thin and all Binance communication is isolated in a dedicated client wrapper.

## Project Structure

```text
trading_bot/
  bot/
    __init__.py
    client.py
    presenters.py
    orders.py
    validators.py
    logging_config.py
  cli.py
  web.py
  static/
    app.js
    styles.css
  templates/
    index.html
  README.md
  requirements.txt
```

## Requirements

- Python 3.10+ recommended
- Binance Futures Demo Trading API key and secret

## Setup

1. Create and activate a virtual environment.

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

2. Install dependencies.

```bash
pip install -r requirements.txt
```

3. Set your environment variables.

Linux/macOS:

```bash
export BINANCE_API_KEY="your_testnet_key"
export BINANCE_API_SECRET="your_testnet_secret"
```

Windows PowerShell:

```powershell
$env:BINANCE_API_KEY="your_testnet_key"
$env:BINANCE_API_SECRET="your_testnet_secret"
```

Optional: because the project uses `python-dotenv`, you can also place these variables in a local `.env` file in the project root. A starter template is included as `.env.example`.

Example `.env`:

```dotenv
BINANCE_API_KEY=your_testnet_key
BINANCE_API_SECRET=your_testnet_secret
```

## How To Get Binance Futures Demo Trading API Keys

1. Open Binance Demo Trading: `https://demo.binance.com`
2. Sign in with your Binance account or create one first.
3. Open API Management: `https://demo.binance.com/en/my/settings/api-management`
4. Create a new API key pair.
5. Export the values into `BINANCE_API_KEY` and `BINANCE_API_SECRET`.

Important:

- These must be Binance Futures Demo Trading credentials, not Binance Spot production keys.
- Binance's current USD-M Futures demo REST base URL is `https://demo-fapi.binance.com`.
- Demo balances and orders are separate from production.

## Run The Browser UI

Start the local web app from the `trading_bot` directory:

```bash
python web.py
```

Then open:

```text
http://127.0.0.1:8000
```

The UI lets you:

- Enter symbol, side, type, quantity, and price
- Submit MARKET and LIMIT orders
- See structured request and response summaries
- Read clear error messages without using the terminal

## CLI Usage

Run commands from the `trading_bot` directory.

### Place a LIMIT order

```bash
python cli.py place-order --symbol BTCUSDT --side BUY --type LIMIT --quantity 0.001 --price 50000
```

### Place a MARKET order

```bash
python cli.py place-order --symbol BTCUSDT --side SELL --type MARKET --quantity 0.001
```

## Console Output

The CLI prints:

- Order Request Summary
- Order Response
- Final Status

Example success output:

```text
Order Request Summary:
- Symbol: BTCUSDT
- Side: BUY
- Type: LIMIT
- Quantity: 0.001
- Price: 50000

Order Response:
- orderId: 123456789
- status: NEW
- executedQty: 0

Final Status:
- SUCCESS
```

## Logging

- Log file: `trading_bot.log`
- Log level: `DEBUG`
- Logged events:
  - Exchange metadata requests
  - Order submission requests
  - API responses
  - Validation failures
  - Exceptions and network/API errors

## Validation Rules

The CLI validates:

- Symbol format
- Side values (`BUY`, `SELL`)
- Type values (`MARKET`, `LIMIT`)
- Quantity must be a positive decimal
- Price is required for `LIMIT`
- Price must not be passed for `MARKET`

Before placing an order, the service also checks Binance exchange metadata to validate:

- Symbol availability on Binance Futures Demo Trading
- Trading status
- Quantity step size and min/max quantity
- Price tick size and min/max price for limit orders

## Error Handling

The application returns clean CLI errors for:

- Missing environment variables
- Invalid input
- Binance API errors
- Network/request failures
- Unsupported or unavailable symbols

## Assumptions

- The tool targets Binance USDT-M Futures Demo Trading only.
- `LIMIT` orders are submitted with `timeInForce=GTC`.
- The response uses `newOrderRespType=RESULT` so market orders can return execution details when Binance provides them.
- The browser UI runs locally on `127.0.0.1:8000`.
- The user runs commands from the project root: `trading_bot/`.

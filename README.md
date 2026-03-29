# Binance Futures Demo Trading Bot

I built this project to place Binance USDT-M Futures demo orders without depending on the Binance UI every time I want to test something.

It supports:

- a browser UI
- a Typer CLI
- MARKET and LIMIT orders
- Binance Demo Trading API keys from environment variables
- validation before the order is sent
- local DEBUG logging

This project is for Binance Demo Trading only, not live trading.

## Project structure

```text
trading_bot/
  bot/
    __init__.py
    client.py
    logging_config.py
    orders.py
    presenters.py
    validators.py
  public/
    assets/
      app.js
      styles.css
  templates/
    index.html
  app.py
  cli.py
  web.py
  README.md
  requirements.txt
```

## Tech used

- Python 3.x
- `python-binance`
- `Typer`
- `FastAPI`
- `python-dotenv`
- Python `logging`

## Binance demo API keys

You need Binance Demo Trading API keys for USDT-M Futures.

Get them from:

1. [https://demo.binance.com/](https://demo.binance.com/)
2. Log in to your Binance account
3. Open Demo Trading
4. Go to API Management:
   [https://demo.binance.com/en/my/settings/api-management](https://demo.binance.com/en/my/settings/api-management)
5. Create a new API key
6. Copy the API key and secret key

If Binance shows multiple key types, use the regular HMAC API key and secret pair.

## Local setup

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```dotenv
BINANCE_API_KEY=your_demo_api_key
BINANCE_API_SECRET=your_demo_api_secret
```

Keep `.env` out of Git.

## Run the UI

```bash
python web.py
```

Then open:

```text
http://127.0.0.1:8000
```

## Run the CLI

LIMIT order:

```bash
python cli.py place-order --symbol BTCUSDT --side BUY --type LIMIT --quantity 0.002 --price 50000
```

MARKET order:

```bash
python cli.py place-order --symbol BTCUSDT --side BUY --type MARKET --quantity 0.002
```

## Validation rules

The app checks:

- symbol validity
- side must be `BUY` or `SELL`
- type must be `MARKET` or `LIMIT`
- `price` is required for `LIMIT`
- `price` is not allowed for `MARKET`
- Binance symbol filters for quantity and price
- `GTC` for limit orders

It also turns common Binance failures into cleaner messages, including:

- invalid credentials
- timestamp drift
- insufficient margin
- minimum notional issues
- restricted-location rejections

## Logging

For local runs, logs go to:

```text
trading_bot.log
```

The log includes:

- API requests
- API responses
- validation errors
- exceptions

## Quantity note

For `BTCUSDT`, quantity is in BTC, not in dollars.

Examples:

- `0.002` means `0.002 BTC`
- `2` means `2 BTC`

So if you submit `2`, Binance may reject it because the order is much larger than expected.

## Vercel deployment

This project can be deployed on Vercel.

When Vercel asks for the application preset, choose:

- `FastAPI`

### Vercel settings

- Application Preset: `FastAPI`
- Root Directory: use the repo root if this repo is already the `trading_bot` project
- Build Command: leave empty
- Output Directory: leave empty

### Vercel environment variables

Add these in Vercel Project Settings:

- `BINANCE_API_KEY`
- `BINANCE_API_SECRET`

### Region note for Binance

Vercel Functions run in `iad1` (Washington, D.C.) by default. Binance can reject requests from that backend location even if you are personally in an allowed country, because Binance sees the server IP, not your browser location.

This repo includes `vercel.json` with the function region pinned to `bom1` so the backend does not run from the default US region.

If Binance still rejects the deployed backend after that, the likely issue is that Binance is blocking the hosting provider's cloud IP range. In that case, the practical setup is to keep the frontend on Vercel if you want, but run the trading backend on your own machine or a VPS in a Binance-supported region.

### Vercel app entrypoint

The deployment entrypoint is:

- `app.py`

### Static assets

Frontend assets are served from:

- `public/assets`

## Useful files

- `web.py` -> runs the browser UI locally
- `cli.py` -> command-line entry point
- `app.py` -> Vercel FastAPI entrypoint
- `bot/client.py` -> Binance Futures API wrapper
- `bot/orders.py` -> order logic
- `bot/validators.py` -> input validation
- `bot/logging_config.py` -> logging setup

## Note

If you ever exposed a demo API key while testing, revoke it in Binance Demo Trading and create a new one.

## Reference

Vercel FastAPI docs:

[https://vercel.com/docs/frameworks/backend/fastapi](https://vercel.com/docs/frameworks/backend/fastapi)

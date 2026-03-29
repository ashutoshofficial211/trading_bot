# Binance Futures Demo Trading Bot

I built this project to place Binance USDT-M Futures demo orders without working directly in the Binance interface every time.

It supports:

- a browser UI
- a Typer CLI
- MARKET and LIMIT orders
- Binance Demo Trading API keys from environment variables
- validation before the order is sent
- file-based logging for local runs

This project uses Binance Futures Demo Trading, not live trading.

## What is inside

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
- Python `logging`
- `python-dotenv`

## Before you start

You need Binance Demo Trading API keys for USDT-M Futures.

Do not use live Binance keys here.

## How to get Binance Demo Trading API keys

1. Go to [Binance Demo Trading](https://demo.binance.com/).
2. Log in to your Binance account.
3. Open Demo Trading.
4. Go to API Management:
   [https://demo.binance.com/en/my/settings/api-management](https://demo.binance.com/en/my/settings/api-management)
5. Create a new API key.
6. Copy the API key and secret key.

If Binance shows multiple key types, use the regular API key + secret key pair that works with HMAC signing.

## Local setup

Clone the repo and install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```dotenv
BINANCE_API_KEY=your_demo_api_key
BINANCE_API_SECRET=your_demo_api_secret
```


## Run the browser UI

```
python web.py
```

Then open:

```text
http://127.0.0.1:8000
```

This is the easiest way to use the app.

## Run the CLI

### LIMIT order

```bash
python cli.py place-order --symbol BTCUSDT --side BUY --type LIMIT --quantity 0.002 --price 50000
```

### MARKET order

```bash
python cli.py place-order --symbol BTCUSDT --side BUY --type MARKET --quantity 0.002
```

## Validation rules

The app checks a few things before sending the order:

- symbol must be valid
- side must be `BUY` or `SELL`
- type must be `MARKET` or `LIMIT`
- `price` is required for `LIMIT`
- `price` is not allowed for `MARKET`
- quantity must respect Binance symbol filters
- limit orders use `GTC`

It also surfaces common Binance errors in a cleaner way, like:

- invalid credentials
- timestamp drift
- insufficient margin
- minimum notional issues

## Logging

For local runs, the app writes DEBUG logs to:

```text
trading_bot.log
```

That includes:

- API requests
- API responses
- validation failures
- exceptions

## Notes on quantity

For `BTCUSDT`, quantity is in BTC, not in dollars.

Example:

- `0.002` means `0.002 BTC`
- `2` means `2 BTC`

So if you submit `2` by mistake, Binance may reject it with an insufficient margin error.

## Vercel deployment

This project can also be deployed on Vercel.

### What to select in Vercel

When Vercel asks for the application preset, choose:

- `FastAPI`

That is the correct preset for this project.


### Static assets

Frontend files are served from:

- `public/assets`

## Important assumption

This project is meant for Binance USDT-M Futures Demo Trading only.

## Useful files

- `web.py` -> runs the browser UI locally
- `cli.py` -> command-line entry point
- `app.py` -> Vercel FastAPI entrypoint
- `bot/client.py` -> Binance Futures API wrapper
- `bot/orders.py` -> order placement logic
- `bot/validators.py` -> request validation
- `bot/logging_config.py` -> logging setup

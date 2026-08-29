# Moomoo market-data client

`moomoo_data.py` retrieves quotes and historical candlesticks through Moomoo's
official OpenD gateway. Your sign-in stays in OpenD; this project does not store
your Moomoo login or trading password.

## One-time setup

1. Install and sign in to Moomoo OpenD, then leave it running. Its usual local
   address is `127.0.0.1:11111`.
2. Install the Python dependency:

   ```bash
   python -m pip install -r requirements-moomoo.txt
   ```

## Use

Moomoo symbols include the market prefix:

```bash
# Latest quotes
python moomoo_data.py quote US.AAPL US.MSFT

# Daily, forward-adjusted candles saved to a CSV
python moomoo_data.py history US.AAPL --start 2026-01-01 --end 2026-08-01 --output data/aapl_daily.csv

# Intraday candles, including US extended hours when your entitlement supports it
python moomoo_data.py history US.AAPL --interval 5m --start 2026-08-01 --end 2026-08-02 --extended-hours
```

For an OpenD instance on another machine, set `MOOMOO_OPEND_HOST` and
`MOOMOO_OPEND_PORT`, or pass `--host` and `--port` to the command.

Quote availability, history depth, and real-time versus delayed data depend on
your Moomoo account's market-data entitlements.

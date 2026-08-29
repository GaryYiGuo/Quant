from moomoo import OpenQuoteContext, RET_OK, Market, SecurityType

quote_ctx = OpenQuoteContext(host="127.0.0.1", port=11111)

try:
    ret, data = quote_ctx.get_stock_basicinfo(
        Market.US,
        SecurityType.STOCK,
        ["US.AAPL", "US.MSFT"],  # optional; omit to request the full market
    )

    if ret == RET_OK:
        print("Connection successful! Stock information:")
        print(data.head())
    else:
        print(f"Error fetching data: {data}")
finally:
    quote_ctx.close()
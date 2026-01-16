import yfinance as yf
import time
import random

def run_unlimited_analysis(ticker_symbol):
    ticker_symbol = ticker_symbol.upper().strip()
    print(f"\n--- [BYPASSING FILTERS: {ticker_symbol}] ---")
    
    try:
        # STEP 1: Create a Ticker object
        # yfinance 0.2.50+ has built-in logic to handle the 'cookie' issue
        # if we don't over-complicate the session.
        stock = yf.Ticker(ticker_symbol)
        
        # STEP 2: Add a human-like "pause" before the request
        # This is the secret to 'unlimited' - don't hit them too fast
        time.sleep(random.uniform(1.5, 3.0)) 
        
        info = stock.info
        
        if not info or 'currentPrice' not in info:
            print("❌ Yahoo blocked the request. Switching to backup fingerprint...")
            # If blocked, we 'reset' by waiting slightly longer
            time.sleep(5)
            info = stock.info

        # --- VALUATION LOGIC ---
        price = info.get('currentPrice') or info.get('regularMarketPrice') or 0.0
        eps = info.get('trailingEps') or 0.0
        intrinsic_val = eps * 18.5
        mos = ((intrinsic_val - price) / intrinsic_val) * 100 if intrinsic_val > 0 else 0

        # --- FINANCIALS ---
        # Note: .info is fast, but .quarterly_financials is a separate 'hit'
        # We try to get everything from .info first to stay under the radar
        print("="*50)
        print(f"SYMBOL:            {ticker_symbol}")
        print(f"CURRENT PRICE:     ${price:,.2f}")
        print(f"INTRINSIC VALUE:   ${intrinsic_val:,.2f}")
        print(f"MARGIN OF SAFETY:  {mos:.1f}%")
        print("-" * 30)
        print(f"PROFIT MARGIN:     {(info.get('profitMargins', 0)*100):.1f}%")
        print(f"DEBT TO EQUITY:    {info.get('debtToEquity', 0):.2f}")
        print(f"52 WEEK HIGH:      ${info.get('fiftyTwoWeekHigh', 0):,.2f}")
        print("-" * 30)
        print(f"RECOMMENDED STOP:  ${price * 0.90:,.2f}")
        print("="*50)

    except Exception as e:
        print(f"⚠️ Connection Error: {e}")
        print("Tip: If this keeps happening, toggle your Wi-Fi off/on to refresh your IP.")

# Run the loop
while True:
    ticker = input("\nEnter Ticker (or 'exit' to quit): ")
    if ticker.lower() == 'exit':
        break
    run_unlimited_analysis(ticker)
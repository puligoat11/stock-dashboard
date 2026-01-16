import time
import requests
import pandas as pd

# --- CONFIGURATION ---
# Paste your Alpha Vantage key between the quotes below
API_KEY = 'zWQm9zLBbTG79BNCFOfUERaxDRIQvkxp' 
BASE_URL = 'https://www.alphavantage.co/query?'

def get_data(function, symbol):
    """Helper to fetch data and wait 12s to stay under the free limit."""
    params = {
        'function': function,
        'symbol': symbol,
        'apikey': API_KEY
    }
    response = requests.get(BASE_URL, params=params)
    # Alpha Vantage requires a cooldown for free keys (5 calls per minute)
    time.sleep(12) 
    return response.json()

def run_alpha_analysis(ticker):
    ticker = ticker.upper().strip()
    print(f"\n--- [ESTABLISHING SECURE DATA FEED: {ticker}] ---")
    
    try:
        # 1. Get Real-Time Price
        print("Fetching Price...")
        quote_data = get_data('GLOBAL_QUOTE', ticker)
        price = float(quote_data.get('Global Quote', {}).get('05. price', 0))

        # 2. Get Fundamental Overview (Margins, EPS, ROE)
        print("Fetching Fundamentals...")
        overview = get_data('OVERVIEW', ticker)
        eps = float(overview.get('EPS', 0))
        pe = float(overview.get('PERatio', 0))
        roe = float(overview.get('ReturnOnEquityTTM', 0))
        margin = float(overview.get('ProfitMargin', 0))

        # 3. Get Cash Flow (for FCF)
        print("Fetching Cash Flow...")
        cash_data = get_data('CASH_FLOW', ticker)
        latest_q = cash_data.get('quarterlyReports', [{}])[0]
        fcf = float(latest_q.get('operatingCashflow', 0)) - abs(float(latest_q.get('capitalExpenditures', 0)))

        # 4. Valuation Logic
        intrinsic_val = eps * 18.5
        mos = ((intrinsic_val - price) / intrinsic_val) * 100 if intrinsic_val > 0 else 0

        # --- THE REPORT ---
        print("\n" + "="*50)
        print(f"SYMBOL:            {ticker}")
        print(f"CURRENT PRICE:     ${price:,.2f}")
        print(f"INTRINSIC VALUE:   ${intrinsic_val:,.2f}")
        print(f"MARGIN OF SAFETY:  {mos:.1f}%")
        print("-" * 30)
        print(f"P/E RATIO:         {pe:.2f}")
        print(f"PROFIT MARGIN:     {margin*100:.1f}%")
        print(f"RETURN ON EQUITY:  {roe*100:.1f}%")
        print(f"QUARTERLY FCF:     ${fcf:,.0f}")
        print("-" * 30)
        print(f"RECOMMENDED STOP:  ${price * 0.90:,.2f} (10%)")
        print("="*50)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Possible Issue: You may have reached your 25-call daily limit.")

# Terminal Command Loop
while True:
    val = input("\nEnter Ticker (or 'exit'): ")
    if val.lower() == 'exit': break
    run_alpha_analysis(val)
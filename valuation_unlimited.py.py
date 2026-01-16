import yfinance as yf
import pandas as pd
import requests
import random
import time

# Identity rotation to stay undetected
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
]

def get_stealth_session():
    """Creates a session that mimics a real human browser."""
    session = requests.Session()
    session.headers.update({
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    })
    return session

def run_analysis(ticker_symbol):
    ticker_symbol = ticker_symbol.upper().strip()
    print(f"\n--- [SECURE CONNECTION ESTABLISHED: {ticker_symbol}] ---")
    
    try:
        # 1. Establish session and add human-like delay
        session = get_stealth_session()
        time.sleep(random.uniform(1, 3)) # Mimic 'thinking' time
        
        stock = yf.Ticker(ticker_symbol, session=session)
        info = stock.info
        
        # 2. Extract Price & Valuation (with fallbacks for 0s)
        price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose') or 0.0
        pe = info.get('trailingPE') or 0.0
        eps = info.get('trailingEps') or 0.0
        intrinsic_val = eps * (8.5 + 10)
        
        # 3. Quarterly Reports
        income_q = stock.quarterly_financials
        cash_q = stock.quarterly_cashflow
        
        q_rev, q_margin, q_ebitda, q_fcf = 0.0, 0.0, 0.0, 0.0
        
        if not income_q.empty:
            latest = income_q.iloc[:, 0]
            q_rev = latest.get('Total Revenue') or 0.0
            gross_p = latest.get('Gross Profit') or 0.0
            q_ebitda = latest.get('EBITDA') or 0.0
            q_margin = (gross_p / q_rev * 100) if q_rev > 0 else 0.0

        if not cash_q.empty:
            latest_cf = cash_q.iloc[:, 0]
            op_cash = latest_cf.get('Operating Cash Flow') or 0.0
            capex = abs(latest_cf.get('Capital Expenditure') or 0.0)
            q_fcf = op_cash - capex

        # 4. Revenue Growth
        annual_f = stock.financials
        rev_history = []
        if not annual_f.empty and 'Total Revenue' in annual_f.index:
            rev_history = annual_f.loc['Total Revenue'].head(3).tolist()[::-1]
        
        growth_status = "GROWING" if len(rev_history) > 1 and rev_history[-1] > rev_history[0] else "STAGNANT"

        # 5. Buffett Score
        margin = info.get('profitMargins') or 0.0
        roe = info.get('returnOnEquity') or 0.0
        debt_to_eq = (info.get('debtToEquity') or 0.0) / 100
        score = sum([margin > 0.20, roe > 0.15, debt_to_eq < 0.6])
        print(f"Buffett Score:     {score}/3")
        print(f"Profit Margin:     {margin*100:.1f}%")
        print(f"Return on Equity:  {roe*100:.1f}%")
        print(f"Debt-to-Equity:    {debt_to_eq:.2f}")
        print("-" * 30)
        print(f"LATEST QUARTERLY EARNINGS:")
        print(f"Revenue:           ${q_rev:,.0f}")
        print(f"Gross Margin:      {q_margin:.1f}%")
        print(f"EBITDA:            ${q_ebitda:,.0f}")
        print(f"Free Cash Flow:    ${q_fcf:,.0f}")
        print("-" * 30)
        print(f"52W High/Low:      ${high_52:,.2f} / ${low_52:,.2f}")
        print(f"RECOMMENDED STOP:  ${stop_loss:,.2f}")
        print("="*50)

    except Exception as e:
        print(f"Data Retrieval Error: {e}")

# Command line input
ticker = input("Enter Ticker: ")
run_stealth_analysis(ticker)
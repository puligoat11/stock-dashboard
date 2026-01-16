import yfinance as yf
import pandas as pd
import requests

# Mimics a real user browser to avoid "Bot" detection
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
}

def run_stealth_analysis(ticker_symbol):
    ticker_symbol = ticker_symbol.upper().strip()
    print(f"\n--- [SECURE CONNECTION ESTABLISHED: {ticker_symbol}] ---")
    
    try:
        # Create a persistent session to look like a human visitor
        session = requests.Session()
        session.headers.update(HEADERS)
        
        # Initialize Ticker with the session
        stock = yf.Ticker(ticker_symbol, session=session)
        info = stock.info
        
        # 1. CORE PRICE & VALUATION (With Robust Fallbacks)
        price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose') or 0.0
        pe = info.get('trailingPE') or 0.0
        eps = info.get('trailingEps') or 0.0
        high_52 = info.get('fiftyTwoWeekHigh') or 0.0
        low_52 = info.get('fiftyTwoWeekLow') or 0.0
        
        # 2. FINANCIAL STATEMENTS
        income_q = stock.quarterly_financials
        annual_f = stock.financials
        cash_q = stock.quarterly_cashflow

        # Extract 3-Year Revenue Growth
        rev_history = []
        if not annual_f.empty and 'Total Revenue' in annual_f.index:
            rev_history = annual_f.loc['Total Revenue'].head(3).tolist()[::-1]
        
        growth_status = "GROWING" if len(rev_history) > 1 and rev_history[-1] > rev_history[0] else "STAGNANT/DECLINING"

        # 3. LATEST QUARTERLY DATA (Avoids the $0 issue)
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

        # 4. BUFFETT SCORECARD
        margin = info.get('profitMargins') or 0.0
        roe = info.get('returnOnEquity') or 0.0
        debt_to_eq = (info.get('debtToEquity') or 0.0) / 100
        
        score = 0
        if margin > 0.20: score += 1
        if roe > 0.15: score += 1
        if debt_to_eq < 0.6: score += 1

        # 5. VALUATION CALCULATIONS
        intrinsic_val = eps * (8.5 + 10) 
        stop_loss = price * 0.90

        # --- THE MASTER REPORT ---
        print("="*50)
        print(f"Current Price:     ${price:,.2f} | P/E: {pe:.2f}")
        print(f"Intrinsic Value:   ${intrinsic_val:,.2f}")
        print(f"3-Year Revenue:    {['${:,.0f}'.format(r) for r in rev_history]}")
        print(f"Growth Status:     {growth_status}")
        print("-" * 30)
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
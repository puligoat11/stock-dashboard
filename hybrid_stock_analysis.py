import yfinance as yf
import pandas as pd
from tabulate import tabulate

def get_clean_df(df):
    """Standardizes yfinance dataframes: newest dates first, clean indices."""
    if df is None or df.empty:
        return None
    # Ensure columns are datetime and sorted newest to oldest
    df.columns = pd.to_datetime(df.columns)
    df = df.sort_index(axis=1, ascending=False)
    return df

def get_window_sum(df, labels, offset, length):
    """Safely sums a range of quarters (e.g., offset=0, length=4 for current TTM)."""
    if df is None: return None
    for label in labels:
        if label in df.index:
            data = df.loc[label].dropna()
            if len(data) >= (offset + length):
                return data.iloc[offset : offset + length].sum()
    return None

def calculate_fcf_ttm(cf_df, offset=0):
    """Calculates FCF for a specific 4-quarter window."""
    if cf_df is None: return None
    # Try direct FCF label
    fcf = get_window_sum(cf_df, ["Free Cash Flow"], offset, 4)
    if fcf is not None: return fcf
    # Fallback to OCF - CapEx
    ocf = get_window_sum(cf_df, ["Operating Cash Flow", "Total Cash From Operating Activities"], offset, 4)
    capex = get_window_sum(cf_df, ["Capital Expenditure", "Purchase of Property Plant Equipment"], offset, 4)
    if ocf is not None and capex is not None:
        return ocf - abs(capex)
    return None

def analyze(tickers):
    rows = []
    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            # 1. Price Data
            hist_6m = t.history(period="6mo")
            hist_1w = t.history(period="10d") # Buffer for holidays
            if hist_6m.empty: raise ValueError("No price data")
            
            price = hist_6m["Close"].iloc[-1]
            r_1d = (price / hist_1w["Close"].iloc[-2] - 1) * 100
            r_1w = (price / hist_1w["Close"].iloc[-6] - 1) * 100
            r_6m = (price / hist_6m["Close"].iloc[0] - 1) * 100

            # 2. Financials
            inc_q = get_clean_df(t.quarterly_financials)
            cf_q = get_clean_df(t.quarterly_cashflow)
            bs = get_clean_df(t.balance_sheet)

            # Revenue TTM & Prior
            rev_ttm = get_window_sum(inc_q, ["Total Revenue"], 0, 4)
            rev_prior = get_window_sum(inc_q, ["Total Revenue"], 4, 4)
            rev_growth = ((rev_ttm - rev_prior) / rev_prior * 100) if rev_ttm and rev_prior else None

            # Margins & Income
            net_inc = get_window_sum(inc_q, ["Net Income"], 0, 4)
            gross_prof = get_window_sum(inc_q, ["Gross Profit"], 0, 4)
            
            # FCF and Valuation
            fcf_val = calculate_fcf_ttm(cf_q, 0)
            eps = t.info.get("trailingEps")
            pe_ratio = price / eps if eps and eps > 0 else None
            
            # Equity for ROE
            equity = bs.loc["Stockholders Equity"].iloc[0] if bs is not None and "Stockholders Equity" in bs.index else None

            rows.append({
                "Ticker": ticker,
                "Price": round(price, 2),
                "1D %": round(r_1d, 2),
                "1W %": round(r_1w, 2),
                "6M %": round(r_6m, 2),
                "PE": round(pe_ratio, 2) if pe_ratio else "N/A",
                "Gross Mgn %": round((gross_prof/rev_ttm)*100, 2) if gross_prof and rev_ttm else "N/A",
                "Net Mgn %": round((net_inc/rev_ttm)*100, 2) if net_inc and rev_ttm else "N/A",
                "FCF ($B)": round(fcf_val/1e9, 2) if fcf_val else "N/A",
                "Rev TTM ($B)": round(rev_ttm/1e9, 2) if rev_ttm else "N/A",
                "Rev Prior ($B)": round(rev_prior/1e9, 2) if rev_prior else "N/A",
                "Rev Grwth %": round(rev_growth, 2) if rev_growth else "N/A"
            })
        except Exception as e:
            rows.append({"Ticker": ticker, "Price": f"Error: {str(e)[:15]}"})
    return pd.DataFrame(rows)

if __name__ == "__main__":
    user_input = input("Enter tickers (e.g. ISRG, AAPL): ").upper().replace(" ", "")
    tickers = [t for t in user_input.split(",") if t]
    df = analyze(tickers)
    print("\n", tabulate(df, headers="keys", tablefmt="github", showindex=False))
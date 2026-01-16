import streamlit as st
import yfinance as yf
import pandas as pd

# Page Config
st.set_page_config(page_title="Stock Analysis Dashboard", layout="wide")

st.title("📈 Hybrid Stock Analysis Dashboard")
ticker_input = st.text_input("Enter Tickers (comma or space separated):", "ISRG, AAPL").upper()
ticker_list = ticker_input.replace(',', ' ').split()

def get_aligned_data(ticker_obj):
    fin = ticker_obj.quarterly_financials
    cf = ticker_obj.quarterly_cashflow
    bs = ticker_obj.quarterly_balance_sheet
    if fin.empty or cf.empty:
        return None, None, None
    for df in [fin, cf, bs]:
        df.columns = [str(c).split(' ')[0] for c in df.columns]
    common_dates = fin.columns.intersection(cf.columns)
    return fin[common_dates[:5]], cf[common_dates[:5]], bs

if st.button("Run Analysis"):
    for ticker_symbol in ticker_list:
        try:
            ticker = yf.Ticker(ticker_symbol)
            financials, cashflow, balance_sheet = get_aligned_data(ticker)
            
            if financials is None:
                st.error(f"Skipping {ticker_symbol}: No financial data found.")
                continue

            f_info = ticker.fast_info
            hist = ticker.history(period="2y")
            current_price = f_info.last_price

            def calc_pct(days_back):
                if len(hist) > days_back:
                    past_price = hist["Close"].iloc[-(days_back + 1)]
                    return ((current_price - past_price) / past_price) * 100
                return 0.0

            st.header(f"Report for: {ticker_symbol}")
            
            # --- MARKET DATA ROW ---
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("Price", f"${current_price:.2f}", f"{calc_pct(1):+.2f}%")
            col2.metric("1-Week", "", f"{calc_pct(5):+.2f}%")
            col3.metric("1-Month", "", f"{calc_pct(21):+.2f}%")
            col4.metric("6-Month", "", f"{calc_pct(126):+.2f}%")
            col5.metric("1-Year", "", f"{calc_pct(252):+.2f}%")

            # --- RATIOS ROW ---
            r1, r2, r3, r4 = st.columns(4)
            r1.write(f"**PE Ratio (TTM):** {ticker.info.get('trailingPE', 'N/A')}")
            r2.write(f"**EPS (TTM):** {ticker.info.get('trailingEps', 'N/A')}")
            
            try:
                d_e = balance_sheet.loc["Total Debt"].iloc[0] / balance_sheet.loc["Stockholders Equity"].iloc[0]
                r3.write(f"**Debt to Equity:** {d_e:.2f}")
            except:
                r3.write("**Debt to Equity:** N/A")
            r4.write(f"**Market Cap:** ${f_info.market_cap / 1e9:.2f}B")

            # --- FINANCIALS TABLE ---
            st.subheader("Quarterly Financials")
            rev = financials.loc["Total Revenue"]
            net_inc = financials.loc["Net Income"]
            ebitda = financials.loc["EBITDA"] if "EBITDA" in financials.index else None
            
            rev_growth = ((rev.iloc[:4] - rev.iloc[1:5].values) / rev.iloc[1:5].values) * 100
            net_margin = (net_inc.iloc[:4] / rev.iloc[:4]) * 100

            display_fin = pd.DataFrame(index=["Total Revenue ($B)", "Rev Growth %", "Net Income ($B)", "Net Margin %", "EBITDA ($B)"])
            for i in range(4):
                display_fin[rev.index[i]] = [round(rev.iloc[i]/1e9, 2), f"{rev_growth.iloc[i]:+.2f}%", 
                                            round(net_inc.iloc[i]/1e9, 2), f"{net_margin.iloc[i]:.2f}%", 
                                            round(ebitda.iloc[i]/1e9, 2) if ebitda is not None else "N/A"]
            
            rev_ttm = rev.iloc[:4].sum()
            display_fin["TTM"] = [round(rev_ttm/1e9, 2), f"{((rev_ttm - rev.iloc[1:5].sum())/rev.iloc[1:5].sum()*100):+.2f}%",
                                  round(net_inc.iloc[:4].sum()/1e9, 2), f"{(net_inc.iloc[:4].sum()/rev_ttm*100):.2f}%",
                                  round(ebitda.iloc[:4].sum()/1e9, 2) if ebitda is not None else "N/A"]
            st.table(display_fin)

            # --- CASH FLOW TABLE ---
            st.subheader("Quarterly Cash Flow")
            ocf, capex = cashflow.loc["Operating Cash Flow"], cashflow.loc["Capital Expenditure"]
            display_cf = pd.DataFrame(index=["Operating Cash Flow ($B)", "Capital Expenditure ($B)"])
            for i in range(4):
                display_cf[ocf.index[i]] = [round(ocf.iloc[i]/1e9, 2), round(capex.iloc[i]/1e9, 2)]
            display_cf["TTM"] = [round(ocf.iloc[:4].sum()/1e9, 2), round(capex.iloc[:4].sum()/1e9, 2)]
            st.table(display_cf)

            # --- FCF FINAL ---
            fcf_ttm = (ocf.iloc[:4].sum() - abs(capex.iloc[:4].sum())) / 1e9
            fcf_yield = (fcf_ttm / (f_info.market_cap / 1e9) * 100)
            
            c1, c2 = st.columns(2)
            c1.info(f"**Calculated TTM FCF:** ${fcf_ttm:.2f} Billion")
            c2.success(f"**Free Cash Flow Yield:** {fcf_yield:.2f}%")
            
            st.divider()

        except Exception as e:
            st.error(f"Error processing {ticker_symbol}: {e}")
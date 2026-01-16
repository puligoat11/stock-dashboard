import dash
from dash import dcc, html, dash_table, Input, Output, State, callback_context, ALL
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import json
import os
import uuid
import base64
import csv
import io

# Load environment variables for cloud deployment
from dotenv import load_dotenv
load_dotenv()

# Check if we should use cloud database or local files
USE_CLOUD_DB = os.getenv("SUPABASE_URL") is not None

if USE_CLOUD_DB:
    # Use Supabase for cloud deployment
    from database import (
        load_watchlist, save_watchlist,
        load_portfolio, save_portfolio,
        load_portfolio_history, save_portfolio_history,
        load_trades, save_trades,
        load_income, save_income,
        load_expenses, save_expenses,
        load_alerts, save_alerts,
        load_settings, save_settings
    )
else:
    # Use local JSON files for development
    # File paths for persistence
    WATCHLIST_FILE = os.path.join(os.path.dirname(__file__), "watchlist.json")
    PORTFOLIO_FILE = os.path.join(os.path.dirname(__file__), "portfolio.json")
    PORTFOLIO_HISTORY_FILE = os.path.join(os.path.dirname(__file__), "portfolio_history.json")
    TRADES_FILE = os.path.join(os.path.dirname(__file__), "trades.json")
    INCOME_FILE = os.path.join(os.path.dirname(__file__), "income.json")
    EXPENSES_FILE = os.path.join(os.path.dirname(__file__), "expenses.json")
    ALERTS_FILE = os.path.join(os.path.dirname(__file__), "alerts.json")
    SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "settings.json")

    def load_watchlist():
        """Load watchlist from JSON file"""
        if os.path.exists(WATCHLIST_FILE):
            try:
                with open(WATCHLIST_FILE, 'r') as f:
                    return json.load(f)
            except:
                return {"tickers": []}
        return {"tickers": []}

    def save_watchlist(data):
        """Save watchlist to JSON file"""
        with open(WATCHLIST_FILE, 'w') as f:
            json.dump(data, f, indent=2)

    def load_portfolio():
        """Load portfolio from JSON file"""
        if os.path.exists(PORTFOLIO_FILE):
            try:
                with open(PORTFOLIO_FILE, 'r') as f:
                    return json.load(f)
            except:
                return {"accounts": []}
        return {"accounts": []}

    def save_portfolio(data):
        """Save portfolio to JSON file"""
        with open(PORTFOLIO_FILE, 'w') as f:
            json.dump(data, f, indent=2)

    def load_portfolio_history():
        """Load portfolio history from JSON file"""
        if os.path.exists(PORTFOLIO_HISTORY_FILE):
            try:
                with open(PORTFOLIO_HISTORY_FILE, 'r') as f:
                    return json.load(f)
            except:
                return {"snapshots": []}
        return {"snapshots": []}

    def save_portfolio_history(data):
        """Save portfolio history to JSON file"""
        with open(PORTFOLIO_HISTORY_FILE, 'w') as f:
            json.dump(data, f, indent=2)

    def load_trades():
        """Load trades from JSON file"""
        if os.path.exists(TRADES_FILE):
            try:
                with open(TRADES_FILE, 'r') as f:
                    return json.load(f)
            except:
                return {"trades": []}
        return {"trades": []}

    def save_trades(data):
        """Save trades to JSON file"""
        with open(TRADES_FILE, 'w') as f:
            json.dump(data, f, indent=2)

    def load_income():
        """Load income from JSON file"""
        default_data = {
            "income": [],
            "recurring": [],
            "rsus": []
        }
        if os.path.exists(INCOME_FILE):
            try:
                with open(INCOME_FILE, 'r') as f:
                    data = json.load(f)
                    if "recurring" not in data:
                        data["recurring"] = []
                    if "rsus" not in data:
                        data["rsus"] = []
                    return data
            except:
                return default_data
        return default_data

    def save_income(data):
        """Save income to JSON file"""
        with open(INCOME_FILE, 'w') as f:
            json.dump(data, f, indent=2)

    def load_expenses():
        """Load expenses from JSON file"""
        default_categories = ["Dining", "Shopping", "Gas", "Entertainment", "Bills", "Travel", "Subscriptions", "Other"]
        default_data = {"expenses": [], "categories": default_categories, "budgets": {}}
        if os.path.exists(EXPENSES_FILE):
            try:
                with open(EXPENSES_FILE, 'r') as f:
                    data = json.load(f)
                    if "budgets" not in data:
                        data["budgets"] = {}
                    if "Food" in data.get("categories", []):
                        data["categories"] = default_categories
                    return data
            except:
                return default_data
        return default_data

    def save_expenses(data):
        """Save expenses to JSON file"""
        with open(EXPENSES_FILE, 'w') as f:
            json.dump(data, f, indent=2)

    def load_alerts():
        """Load alerts from JSON file"""
        if os.path.exists(ALERTS_FILE):
            try:
                with open(ALERTS_FILE, 'r') as f:
                    return json.load(f)
            except:
                return {"alerts": []}
        return {"alerts": []}

    def save_alerts(data):
        """Save alerts to JSON file"""
        with open(ALERTS_FILE, 'w') as f:
            json.dump(data, f, indent=2)

    def load_settings():
        """Load settings from JSON file"""
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    return json.load(f)
            except:
                return {"target_allocations": {}, "rebalance_threshold": 5}
        return {"target_allocations": {}, "rebalance_threshold": 5}

    def save_settings(data):
        """Save settings to JSON file"""
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(data, f, indent=2)

# Initialize the Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
app.title = "Stock Analysis Dashboard"

# Expose server for Gunicorn (cloud deployment)
server = app.server

# Capital One category mapping
CAPITAL_ONE_CATEGORY_MAP = {
    "Dining": "Dining",
    "Merchandise": "Shopping",
    "Gas/Automotive": "Gas",
    "Entertainment": "Entertainment",
    "Other Services": "Bills",
    "Professional Services": "Bills",
    "Other Travel": "Travel",
    "Airfare": "Travel",
    "Phone/Cable": "Subscriptions",
    "Other": "Other"
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def record_portfolio_snapshot():
    """Record current portfolio values as a daily snapshot"""
    today = datetime.now().strftime("%Y-%m-%d")
    history = load_portfolio_history()
    portfolio = load_portfolio()

    # Check if we already have a snapshot for today
    existing_dates = [s['date'] for s in history.get('snapshots', [])]
    if today in existing_dates:
        # Update today's snapshot instead of adding new one
        for snapshot in history['snapshots']:
            if snapshot['date'] == today:
                history['snapshots'].remove(snapshot)
                break

    # Calculate current values for each account
    accounts_data = {}
    total_value = 0
    total_cost = 0

    for account in portfolio.get('accounts', []):
        account_value = 0
        account_cost = 0

        for holding in account.get('holdings', []):
            try:
                ticker = yf.Ticker(holding['ticker'])
                hist = ticker.history(period="1d")
                if not hist.empty:
                    current_price = hist['Close'].iloc[-1]
                    value = current_price * holding['shares']
                    cost = holding['avg_cost'] * holding['shares']
                    account_value += value
                    account_cost += cost
            except:
                continue

        accounts_data[account['id']] = {
            'name': account['name'],
            'value': account_value,
            'cost': account_cost
        }
        total_value += account_value
        total_cost += account_cost

    # Create snapshot
    snapshot = {
        'date': today,
        'accounts': accounts_data,
        'total_value': total_value,
        'total_cost': total_cost
    }

    history['snapshots'].append(snapshot)
    # Keep only last 365 days of data
    history['snapshots'] = sorted(history['snapshots'], key=lambda x: x['date'])[-365:]
    save_portfolio_history(history)

    return snapshot

# ============================================================================
# CUSTOM CSS
# ============================================================================

app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            body {
                background-color: #f0f7ff;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
            .main-header {
                background: linear-gradient(135deg, #1a73e8 0%, #0d47a1 100%);
                color: white;
                padding: 20px 30px;
                border-radius: 0 0 20px 20px;
                margin-bottom: 30px;
                box-shadow: 0 4px 15px rgba(26, 115, 232, 0.3);
            }
            .header-content {
                display: flex;
                justify-content: space-between;
                align-items: center;
                max-width: 1600px;
                margin: 0 auto;
            }
            .header-title {
                margin: 0;
                font-size: 1.8rem;
                font-weight: 600;
            }
            .header-nav a {
                color: white;
                text-decoration: none;
                margin-left: 25px;
                font-weight: 500;
                opacity: 0.9;
                transition: opacity 0.2s;
            }
            .header-nav a:hover {
                opacity: 1;
                text-decoration: underline;
            }
            .search-container {
                background: white;
                padding: 25px;
                border-radius: 15px;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.08);
                margin-bottom: 25px;
            }
            .search-input {
                border: 2px solid #e3f2fd !important;
                border-radius: 25px !important;
                padding: 12px 20px !important;
                font-size: 16px !important;
                transition: all 0.3s ease;
            }
            .search-input:focus {
                border-color: #1a73e8 !important;
                box-shadow: 0 0 0 3px rgba(26, 115, 232, 0.2) !important;
            }
            .search-btn {
                border-radius: 25px !important;
                padding: 12px 30px !important;
                background: linear-gradient(135deg, #1a73e8 0%, #0d47a1 100%) !important;
                border: none !important;
                font-weight: 600 !important;
                transition: all 0.3s ease;
            }
            .search-btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 15px rgba(26, 115, 232, 0.4) !important;
            }
            .nav-card {
                background: white;
                border-radius: 15px;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.08);
                padding: 20px;
                cursor: pointer;
                transition: all 0.3s ease;
                text-decoration: none;
                display: block;
                color: inherit;
                height: 100%;
            }
            .nav-card:hover {
                transform: translateY(-3px);
                box-shadow: 0 6px 20px rgba(26, 115, 232, 0.2);
                text-decoration: none;
                color: inherit;
            }
            .nav-card-header {
                background: linear-gradient(135deg, #1a73e8 0%, #4285f4 100%);
                color: white;
                padding: 15px 20px;
                border-radius: 10px;
                font-size: 1.2rem;
                font-weight: 600;
                margin-bottom: 15px;
                text-align: center;
            }
            .stock-card {
                background: white;
                border-radius: 15px;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.08);
                margin-bottom: 25px;
                overflow: hidden;
            }
            .stock-card-header {
                background: linear-gradient(135deg, #1a73e8 0%, #4285f4 100%);
                color: white;
                padding: 20px 25px;
                font-size: 1.4rem;
                font-weight: 600;
            }
            .stock-card-body {
                padding: 25px;
            }
            .section-title {
                color: #1a73e8;
                font-weight: 600;
                margin: 25px 0 15px 0;
                padding-bottom: 10px;
                border-bottom: 2px solid #e3f2fd;
            }
            .fcf-box {
                background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
                border-radius: 10px;
                padding: 20px;
                text-align: center;
                border-left: 4px solid #1a73e8;
            }
            .fcf-box.success {
                background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
                border-left-color: #2e7d32;
            }
            .fcf-label {
                color: #666;
                font-size: 0.9rem;
                margin-bottom: 5px;
            }
            .fcf-value {
                color: #1a73e8;
                font-size: 1.5rem;
                font-weight: 700;
            }
            .fcf-box.success .fcf-value {
                color: #2e7d32;
            }
            .dash-table-container {
                border-radius: 10px;
                overflow: hidden;
            }
            .negative-value {
                color: #dc3545 !important;
                font-weight: 600;
            }
            .info-panel {
                background: #f8fbff;
                border-radius: 10px;
                padding: 15px;
                height: 100%;
            }
            .info-section {
                background: white;
                border-radius: 10px;
                padding: 15px;
                margin-bottom: 15px;
                box-shadow: 0 1px 5px rgba(0,0,0,0.05);
            }
            .info-section-title {
                color: #1a73e8;
                font-weight: 600;
                font-size: 1rem;
                margin-bottom: 12px;
                padding-bottom: 8px;
                border-bottom: 2px solid #e3f2fd;
            }
            .news-item {
                padding: 10px 0;
                border-bottom: 1px solid #eee;
            }
            .news-item:last-child {
                border-bottom: none;
            }
            .news-title {
                color: #1a73e8;
                font-size: 0.9rem;
                text-decoration: none;
                font-weight: 500;
            }
            .news-title:hover {
                text-decoration: underline;
            }
            .news-meta {
                color: #888;
                font-size: 0.75rem;
                margin-top: 4px;
            }
            .analyst-rating {
                display: inline-block;
                padding: 5px 12px;
                border-radius: 15px;
                font-weight: 600;
                font-size: 0.85rem;
            }
            .rating-buy {
                background: #e8f5e9;
                color: #2e7d32;
            }
            .rating-hold {
                background: #fff3e0;
                color: #f57c00;
            }
            .rating-sell {
                background: #ffebee;
                color: #c62828;
            }
            .price-target {
                font-size: 0.9rem;
                margin: 8px 0;
            }
            .earnings-date {
                background: #e3f2fd;
                padding: 10px;
                border-radius: 8px;
                margin: 5px 0;
            }
            .watchlist-preview {
                max-height: 400px;
                overflow-y: auto;
            }
            .watchlist-row {
                display: flex;
                justify-content: space-between;
                padding: 12px 15px;
                border-bottom: 1px solid #e3f2fd;
                align-items: center;
            }
            .watchlist-row:last-child {
                border-bottom: none;
            }
            .watchlist-ticker {
                font-weight: 600;
                color: #1a73e8;
                font-size: 1rem;
            }
            .watchlist-price {
                font-weight: 500;
                color: #333;
            }
            .watchlist-change {
                font-weight: 600;
                font-size: 0.85rem;
            }
            .positive {
                color: #2e7d32;
            }
            .negative {
                color: #dc3545;
            }
            .account-summary {
                padding: 15px;
                background: #f8fbff;
                border-radius: 10px;
                margin-bottom: 10px;
            }
            .account-name {
                font-weight: 600;
                color: #333;
                margin-bottom: 5px;
            }
            .account-value {
                font-size: 1.1rem;
                font-weight: 600;
            }
            .total-row {
                background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
                padding: 15px;
                border-radius: 10px;
                margin-top: 15px;
            }
            .back-btn {
                background: transparent;
                border: 2px solid white;
                color: white;
                padding: 8px 20px;
                border-radius: 20px;
                cursor: pointer;
                transition: all 0.3s;
            }
            .back-btn:hover {
                background: white;
                color: #1a73e8;
            }
            .add-input {
                border: 2px solid #e3f2fd !important;
                border-radius: 10px !important;
                padding: 10px 15px !important;
            }
            .add-btn {
                background: linear-gradient(135deg, #1a73e8 0%, #0d47a1 100%) !important;
                border: none !important;
                border-radius: 10px !important;
                padding: 10px 20px !important;
            }
            .remove-btn {
                background: #ffebee !important;
                color: #c62828 !important;
                border: none !important;
                border-radius: 5px !important;
                padding: 5px 10px !important;
                font-size: 0.8rem !important;
            }
            .empty-state {
                text-align: center;
                padding: 40px;
                color: #888;
            }
            .empty-state-icon {
                font-size: 3rem;
                margin-bottom: 15px;
                opacity: 0.5;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# ============================================================================
# HELPER FUNCTIONS (Original)
# ============================================================================

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

def format_value(val, is_currency=True):
    if val is None or pd.isna(val):
        return "N/A"
    val_millions = val / 1e6
    if val_millions < 0:
        if is_currency:
            return f"({abs(val_millions):,.2f})"
        else:
            return f"({abs(val_millions):.2f})"
    else:
        if is_currency:
            return f"{val_millions:,.2f}"
        else:
            return f"{val_millions:.2f}"

def format_display_value(val):
    if val is None or pd.isna(val):
        return "N/A", False
    if isinstance(val, str):
        return val, False
    val_billions = val / 1e9
    is_negative = val_billions < 0
    if is_negative:
        return f"({abs(val_billions):,.1f})", True
    else:
        return f"{val_billions:,.1f}", False

def create_price_chart(hist):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        vertical_spacing=0.03,
                        row_heights=[0.7, 0.3])
    fig.add_trace(
        go.Scatter(x=hist.index, y=hist['Close'],
                   mode='lines', name='Price',
                   line=dict(color='#1a73e8', width=2)),
        row=1, col=1
    )
    colors = ['#ef5350' if hist['Close'].iloc[i] < hist['Open'].iloc[i]
              else '#26a69a' for i in range(len(hist))]
    fig.add_trace(
        go.Bar(x=hist.index, y=hist['Volume'], name='Volume',
               marker_color=colors, opacity=0.7),
        row=2, col=1
    )
    fig.update_layout(
        height=300,
        margin=dict(l=0, r=0, t=10, b=0),
        showlegend=False,
        xaxis_rangeslider_visible=False,
        plot_bgcolor='white',
        paper_bgcolor='white',
    )
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#f0f0f0')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#f0f0f0')
    fig.update_xaxes(
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1M", step="month", stepmode="backward"),
                dict(count=3, label="3M", step="month", stepmode="backward"),
                dict(count=6, label="6M", step="month", stepmode="backward"),
                dict(count=1, label="1Y", step="year", stepmode="backward"),
                dict(step="all", label="All")
            ]),
            bgcolor='#e3f2fd',
            activecolor='#1a73e8',
            font=dict(color='#333')
        ),
        row=1, col=1
    )
    return fig

def get_news_section(ticker):
    """Get recent news with smart extraction of key points"""
    try:
        # Try to get news data from yfinance - handle different API versions
        news_data = []
        try:
            # Try the news property
            if hasattr(ticker, 'news'):
                raw_news = ticker.news
                # Handle if it's a list or other structure
                if isinstance(raw_news, list):
                    news_data = raw_news
                elif isinstance(raw_news, dict) and 'items' in raw_news:
                    news_data = raw_news.get('items', [])
        except Exception:
            pass

        # If no news from property, try get_news method
        if not news_data:
            try:
                if hasattr(ticker, 'get_news'):
                    news_data = ticker.get_news()
            except Exception:
                pass

        if not news_data or len(news_data) == 0:
            return html.Div([
                html.P("No recent news available", style={"color": "#888", "fontSize": "0.9rem"}),
                html.P("Check back later for updates", style={"color": "#aaa", "fontSize": "0.8rem"})
            ])

        # Process articles - be flexible with field names
        articles = []
        for item in news_data[:10]:  # Check up to 10 articles
            if not isinstance(item, dict):
                continue

            # Try different field names for title
            title = (item.get('title') or item.get('headline') or
                    item.get('name') or item.get('content', {}).get('title', ''))

            if not title:
                continue

            # Try different field names for link
            link = (item.get('link') or item.get('url') or
                   item.get('canonicalUrl', {}).get('url') if isinstance(item.get('canonicalUrl'), dict) else
                   item.get('canonicalUrl') or '#')

            # Try different field names for publisher
            publisher = (item.get('publisher') or item.get('source') or
                        item.get('provider', {}).get('displayName') if isinstance(item.get('provider'), dict) else
                        item.get('provider') or 'News')

            # Try different field names for summary
            summary = (item.get('summary') or item.get('description') or
                      item.get('content', {}).get('summary', '') if isinstance(item.get('content'), dict) else '')

            articles.append({
                'title': title,
                'link': link if isinstance(link, str) else '#',
                'publisher': publisher if isinstance(publisher, str) else 'News',
                'summary': summary if isinstance(summary, str) else ''
            })

        if not articles:
            return html.P("No recent news available", style={"color": "#888", "fontSize": "0.9rem"})

        # Create bullet points from articles (up to 3)
        bullet_items = []
        seen_titles = set()

        for article in articles:
            # Skip duplicates
            title_key = article['title'][:50].lower()
            if title_key in seen_titles:
                continue
            seen_titles.add(title_key)

            # Use summary if available, otherwise use title
            display_text = article['title']
            if article['summary'] and len(article['summary']) > 30:
                first_sentence = article['summary'].split('.')[0].strip()
                if 30 < len(first_sentence) < 200:
                    display_text = first_sentence + "."

            bullet_items.append(
                html.Li([
                    html.A(display_text, href=article['link'], target="_blank",
                          style={"color": "#1a73e8", "textDecoration": "none", "fontSize": "0.9rem"}),
                    html.Span(f" - {article['publisher']}", style={"color": "#888", "fontSize": "0.8rem"})
                ], style={"marginBottom": "8px"})
            )

            if len(bullet_items) >= 3:
                break

        if not bullet_items:
            return html.P("No recent news available", style={"color": "#888", "fontSize": "0.9rem"})

        return html.Ul(bullet_items, style={"paddingLeft": "20px", "margin": "0"})

    except Exception as e:
        return html.P(f"Unable to load news", style={"color": "#888", "fontSize": "0.9rem"})

def get_earnings_section(ticker):
    try:
        calendar = ticker.calendar
        if calendar is None or (isinstance(calendar, pd.DataFrame) and calendar.empty):
            return html.P("No upcoming events scheduled", style={"color": "#888", "fontSize": "0.9rem"})
        events = []
        if isinstance(calendar, dict):
            if 'Earnings Date' in calendar:
                earnings_dates = calendar['Earnings Date']
                if earnings_dates:
                    if isinstance(earnings_dates, list) and len(earnings_dates) > 0:
                        date_str = earnings_dates[0].strftime("%B %d, %Y") if hasattr(earnings_dates[0], 'strftime') else str(earnings_dates[0])
                        events.append(html.Div([
                            html.Strong("Earnings Date: "),
                            html.Span(date_str)
                        ], className="earnings-date"))
            if 'Dividend Date' in calendar and calendar['Dividend Date']:
                div_date = calendar['Dividend Date']
                date_str = div_date.strftime("%B %d, %Y") if hasattr(div_date, 'strftime') else str(div_date)
                events.append(html.Div([
                    html.Strong("Dividend Date: "),
                    html.Span(date_str)
                ], className="earnings-date"))
            if 'Ex-Dividend Date' in calendar and calendar['Ex-Dividend Date']:
                ex_date = calendar['Ex-Dividend Date']
                date_str = ex_date.strftime("%B %d, %Y") if hasattr(ex_date, 'strftime') else str(ex_date)
                events.append(html.Div([
                    html.Strong("Ex-Dividend Date: "),
                    html.Span(date_str)
                ], className="earnings-date"))
        if not events:
            return html.P("No upcoming events scheduled", style={"color": "#888", "fontSize": "0.9rem"})
        return html.Div(events)
    except:
        return html.P("Unable to load calendar", style={"color": "#888", "fontSize": "0.9rem"})

def get_analyst_section(ticker):
    try:
        info = ticker.info
        recommendation = info.get('recommendationKey', 'N/A')
        num_analysts = info.get('numberOfAnalystOpinions', 'N/A')
        rating_class = "rating-hold"
        if recommendation and recommendation.lower() in ['buy', 'strong_buy', 'strongbuy']:
            rating_class = "rating-buy"
            recommendation = "BUY"
        elif recommendation and recommendation.lower() in ['sell', 'strong_sell', 'strongsell']:
            rating_class = "rating-sell"
            recommendation = "SELL"
        elif recommendation:
            recommendation = recommendation.upper().replace('_', ' ')
        target_mean = info.get('targetMeanPrice', None)
        target_high = info.get('targetHighPrice', None)
        target_low = info.get('targetLowPrice', None)
        current_price = info.get('currentPrice', info.get('regularMarketPrice', None))
        elements = []
        if recommendation and recommendation != 'N/A':
            elements.append(html.Div([
                html.Span("Consensus: ", style={"fontWeight": "500"}),
                html.Span(recommendation, className=f"analyst-rating {rating_class}")
            ], style={"marginBottom": "10px"}))
        if num_analysts and num_analysts != 'N/A':
            elements.append(html.Div(f"Based on {num_analysts} analysts",
                                    style={"color": "#666", "fontSize": "0.85rem", "marginBottom": "10px"}))
        if target_mean:
            upside = ""
            if current_price and target_mean:
                pct = ((target_mean - current_price) / current_price) * 100
                color = "#2e7d32" if pct > 0 else "#c62828"
                upside = f" ({pct:+.1f}%)"
                elements.append(html.Div([
                    html.Strong("Target Price: "),
                    html.Span(f"${target_mean:.2f}"),
                    html.Span(upside, style={"color": color, "fontWeight": "600"})
                ], className="price-target"))
        if target_high and target_low:
            elements.append(html.Div([
                html.Strong("Range: "),
                html.Span(f"${target_low:.2f} - ${target_high:.2f}")
            ], className="price-target"))
        if not elements:
            return html.P("No analyst data available", style={"color": "#888", "fontSize": "0.9rem"})
        return html.Div(elements)
    except:
        return html.P("Unable to load analyst data", style={"color": "#888", "fontSize": "0.9rem"})

def create_table(data, columns):
    style_conditions = [
        {'if': {'column_id': 'Metric'}, 'textAlign': 'left', 'fontWeight': '600', 'color': '#333'},
        {'if': {'row_index': 'odd'}, 'backgroundColor': '#f8fbff'},
        {'if': {'column_id': 'TTM'}, 'fontWeight': '700', 'backgroundColor': '#e8f4fd'},
    ]
    for col in columns:
        if col['id'] != 'Metric':
            style_conditions.append({
                'if': {
                    'filter_query': '{' + col['id'] + '} contains "("',
                    'column_id': col['id']
                },
                'color': '#dc3545',
                'fontWeight': '600'
            })
    return dash_table.DataTable(
        data=data,
        columns=columns,
        style_table={'overflowX': 'auto', 'borderRadius': '10px'},
        style_cell={
            'textAlign': 'center',
            'padding': '12px 15px',
            'fontSize': '14px',
            'border': 'none',
            'borderBottom': '1px solid #e3f2fd'
        },
        style_header={
            'backgroundColor': '#1a73e8',
            'color': 'white',
            'fontWeight': '600',
            'border': 'none',
            'padding': '15px'
        },
        style_data={
            'backgroundColor': 'white',
        },
        style_data_conditional=style_conditions
    )

# ============================================================================
# STOCK DATA HELPERS
# ============================================================================

def get_stock_quick_data(ticker_symbol):
    """Get quick stock data for watchlist/portfolio display"""
    try:
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period="1y")  # Get 1 year for 6M calc
        if hist.empty:
            return None

        current_price = hist['Close'].iloc[-1]
        current_date = hist.index[-1]

        def get_price_at_date(target_date):
            """Find price closest to target date (on or before)"""
            valid_dates = hist.index[hist.index <= target_date]
            if len(valid_dates) > 0:
                return hist.loc[valid_dates[-1], 'Close']
            return None

        def calc_return(time_delta):
            """Calculate return from a time period ago"""
            target = current_date - time_delta
            past_price = get_price_at_date(target)
            if past_price is not None and past_price > 0:
                return ((current_price - past_price) / past_price) * 100
            return 0.0

        return {
            "ticker": ticker_symbol,
            "price": current_price,
            "change_1d": calc_return(timedelta(days=1)),           # 1 calendar day ago
            "change_1w": calc_return(timedelta(days=7)),           # 7 calendar days ago
            "change_1m": calc_return(relativedelta(months=1)),     # Exactly 1 month ago
            "change_6m": calc_return(relativedelta(months=6))      # Exactly 6 months ago
        }
    except:
        return None

def format_change(val):
    """Format percentage change with color class"""
    if val >= 0:
        return f"+{val:.2f}%", "positive"
    else:
        return f"{val:.2f}%", "negative"

# ============================================================================
# LANDING PAGE COMPONENTS
# ============================================================================

def create_watchlist_preview():
    """Create watchlist preview for landing page"""
    watchlist = load_watchlist()
    tickers = watchlist.get("tickers", [])

    if not tickers:
        return html.Div([
            html.Div("No stocks in watchlist", className="empty-state"),
            html.P("Click the Watchlist button to add stocks", style={"color": "#888", "textAlign": "center"})
        ])

    rows = []
    for ticker in tickers[:10]:  # Show max 10 on preview
        data = get_stock_quick_data(ticker)
        if data:
            change_1d, class_1d = format_change(data['change_1d'])
            change_1w, class_1w = format_change(data['change_1w'])
            change_1m, class_1m = format_change(data['change_1m'])
            change_6m, class_6m = format_change(data['change_6m'])

            rows.append(html.Div([
                # Ticker as clickable link
                html.A(ticker, href=f"/search?ticker={ticker}",
                      className="watchlist-ticker",
                      style={"width": "60px", "textDecoration": "none", "cursor": "pointer"}),
                html.Span(f"${data['price']:.2f}", className="watchlist-price", style={"width": "80px"}),
                html.Span(change_1d, className=f"watchlist-change {class_1d}", style={"width": "60px"}),
                html.Span(change_1w, className=f"watchlist-change {class_1w}", style={"width": "60px"}),
                html.Span(change_1m, className=f"watchlist-change {class_1m}", style={"width": "60px"}),
                html.Span(change_6m, className=f"watchlist-change {class_6m}", style={"width": "60px"}),
            ], className="watchlist-row"))

    # Header row
    header = html.Div([
        html.Span("Ticker", style={"width": "60px", "fontWeight": "600", "color": "#666"}),
        html.Span("Price", style={"width": "80px", "fontWeight": "600", "color": "#666"}),
        html.Span("1D", style={"width": "60px", "fontWeight": "600", "color": "#666"}),
        html.Span("1W", style={"width": "60px", "fontWeight": "600", "color": "#666"}),
        html.Span("1M", style={"width": "60px", "fontWeight": "600", "color": "#666"}),
        html.Span("6M", style={"width": "60px", "fontWeight": "600", "color": "#666"}),
    ], className="watchlist-row", style={"borderBottom": "2px solid #e3f2fd"})

    return html.Div([header] + rows, className="watchlist-preview")

def create_portfolio_trend_graph(time_filter="1M", selected_accounts=None):
    """Create portfolio trend graph using historical stock prices and trades"""
    portfolio = load_portfolio()
    trades_data = load_trades()
    trades = trades_data.get('trades', [])

    # Determine time period and interval
    today = datetime.now()
    time_config = {
        "1D": {"days": 1, "period": "1d", "interval": "5m"},
        "1W": {"days": 7, "period": "7d", "interval": "1h"},
        "1M": {"days": 30, "period": "1mo", "interval": "1d"},
        "3M": {"days": 90, "period": "3mo", "interval": "1d"},
        "6M": {"days": 180, "period": "6mo", "interval": "1d"},
        "1Y": {"days": 365, "period": "1y", "interval": "1d"},
        "All": {"days": 9999, "period": "max", "interval": "1d"}
    }

    config = time_config.get(time_filter, time_config["1M"])
    cutoff_date = today - timedelta(days=config["days"])

    # Collect all unique tickers from portfolio
    all_holdings = {}
    for account in portfolio.get('accounts', []):
        for holding in account.get('holdings', []):
            ticker = holding['ticker']
            if ticker not in all_holdings:
                all_holdings[ticker] = {'shares': 0, 'avg_cost': 0}
            all_holdings[ticker]['shares'] += holding['shares']

    if not all_holdings:
        return go.Figure().add_annotation(
            text="No holdings to display.",
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color="#888")
        )

    # Fetch historical data for all tickers
    try:
        tickers_str = " ".join(all_holdings.keys())
        hist_data = yf.download(tickers_str, period=config["period"], interval=config["interval"],
                                progress=False, auto_adjust=True, group_by='ticker')

        # Handle single vs multiple tickers
        if len(all_holdings) == 1:
            ticker = list(all_holdings.keys())[0]
            hist_data = {ticker: hist_data}

        # Build portfolio value over time
        portfolio_values = {}

        for ticker, shares_info in all_holdings.items():
            shares = shares_info['shares']
            try:
                if len(all_holdings) == 1:
                    ticker_hist = hist_data[ticker]
                else:
                    ticker_hist = hist_data[ticker] if ticker in hist_data.columns.get_level_values(0) else None

                if ticker_hist is not None and not ticker_hist.empty:
                    close_prices = ticker_hist['Close'] if 'Close' in ticker_hist.columns else ticker_hist
                    for dt, price in close_prices.items():
                        if pd.notna(price):
                            dt_key = dt.strftime("%Y-%m-%d %H:%M") if time_filter in ["1D", "1W"] else dt.strftime("%Y-%m-%d")
                            if dt_key not in portfolio_values:
                                portfolio_values[dt_key] = 0
                            portfolio_values[dt_key] += price * shares
            except Exception:
                continue

        if not portfolio_values:
            # Fallback to stored history
            history = load_portfolio_history()
            snapshots = history.get('snapshots', [])
            for s in snapshots:
                portfolio_values[s['date']] = s.get('total_value', 0)

        # Sort and create graph
        sorted_dates = sorted(portfolio_values.keys())
        values = [portfolio_values[d] for d in sorted_dates]

        # Calculate min/max for Y-axis with padding
        if values:
            min_val = min(values)
            max_val = max(values)
            padding = (max_val - min_val) * 0.1 if max_val != min_val else max_val * 0.05
            y_min = max(0, min_val - padding)
            y_max = max_val + padding
        else:
            y_min, y_max = 0, 100

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=sorted_dates, y=values,
            mode='lines',
            name='Portfolio Value',
            line=dict(color='#1a73e8', width=2),
            fill='tozeroy',
            fillcolor='rgba(26, 115, 232, 0.1)'
        ))

        # Format x-axis based on time period
        if time_filter == "1D":
            xaxis_config = dict(showgrid=True, gridcolor='#f0f0f0', tickformat="%H:%M")
        elif time_filter == "1W":
            xaxis_config = dict(showgrid=True, gridcolor='#f0f0f0', tickformat="%a %H:%M")
        else:
            xaxis_config = dict(showgrid=True, gridcolor='#f0f0f0', tickformat="%b %d")

        fig.update_layout(
            height=250,
            margin=dict(l=10, r=10, t=30, b=10),
            showlegend=False,
            plot_bgcolor='white',
            paper_bgcolor='white',
            xaxis=xaxis_config,
            yaxis=dict(showgrid=True, gridcolor='#f0f0f0', tickprefix='$',
                      range=[y_min, y_max], autorange=False),
            hovermode='x unified'
        )

        return fig

    except Exception as e:
        # Fallback to stored snapshots
        history = load_portfolio_history()
        snapshots = history.get('snapshots', [])

        if not snapshots:
            return go.Figure().add_annotation(
                text="No portfolio history yet.",
                xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
                font=dict(size=14, color="#888")
            )

        dates = [s['date'] for s in snapshots]
        values = [s.get('total_value', 0) for s in snapshots]

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=dates, y=values, mode='lines+markers',
                                 line=dict(color='#1a73e8', width=2)))

        if values:
            min_val = min(values)
            max_val = max(values)
            padding = (max_val - min_val) * 0.1 if max_val != min_val else max_val * 0.05
            y_range = [max(0, min_val - padding), max_val + padding]
        else:
            y_range = [0, 100]

        fig.update_layout(
            height=250,
            margin=dict(l=10, r=10, t=30, b=10),
            plot_bgcolor='white',
            paper_bgcolor='white',
            yaxis=dict(tickprefix='$', range=y_range)
        )

        return fig

def create_portfolio_summary(filter_account=None, filter_ticker=None, filter_date=None):
    """Create portfolio summary for landing page with graph and table"""
    portfolio = load_portfolio()
    accounts = portfolio.get("accounts", [])

    if not accounts:
        return html.Div([
            html.Div("No portfolio accounts", className="empty-state"),
            html.P("Click the button above to set up your portfolio", style={"color": "#888", "textAlign": "center"})
        ])

    # Record snapshot on page load
    try:
        record_portfolio_snapshot()
    except:
        pass

    # Apply account filter
    if filter_account and filter_account != 'ALL':
        accounts = [acc for acc in accounts if acc['id'] == filter_account]

    # Calculate current values
    account_data = []
    holdings_data = []  # For ticker-level detail
    total_value = 0
    total_cost = 0

    for account in accounts:
        account_value = 0
        account_cost = 0

        for holding in account.get("holdings", []):
            # Apply ticker filter
            if filter_ticker and filter_ticker.upper() not in holding["ticker"].upper():
                continue

            data = get_stock_quick_data(holding["ticker"])
            if data:
                current_val = data["price"] * holding["shares"]
                cost_basis = holding["avg_cost"] * holding["shares"]
                account_value += current_val
                account_cost += cost_basis

                # Track individual holdings for detailed view
                gain = current_val - cost_basis
                holdings_data.append({
                    'account': account['name'],
                    'ticker': holding["ticker"],
                    'shares': holding["shares"],
                    'price': data["price"],
                    'value': current_val,
                    'cost': cost_basis,
                    'gain': gain,
                    'gain_pct': (gain / cost_basis * 100) if cost_basis > 0 else 0
                })

        gain_loss = account_value - account_cost
        gain_pct = (gain_loss / account_cost * 100) if account_cost > 0 else 0
        total_value += account_value
        total_cost += account_cost

        if account_value > 0 or account_cost > 0:  # Only show accounts with data after filtering
            account_data.append({
                'id': account['id'],
                'name': account['name'],
                'value': account_value,
                'cost': account_cost,
                'gain_loss': gain_loss,
                'gain_pct': gain_pct
            })

    total_gain = total_value - total_cost
    total_pct = (total_gain / total_cost * 100) if total_cost > 0 else 0

    # Create time filter buttons
    time_buttons = html.Div([
        dbc.ButtonGroup([
            dbc.Button("1D", id="time-1d", color="primary", outline=True, size="sm"),
            dbc.Button("1W", id="time-1w", color="primary", outline=True, size="sm"),
            dbc.Button("1M", id="time-1m", color="primary", size="sm"),
            dbc.Button("3M", id="time-3m", color="primary", outline=True, size="sm"),
            dbc.Button("6M", id="time-6m", color="primary", outline=True, size="sm"),
            dbc.Button("1Y", id="time-1y", color="primary", outline=True, size="sm"),
            dbc.Button("All", id="time-all", color="primary", outline=True, size="sm"),
        ], size="sm")
    ], style={"marginBottom": "10px"})

    # Create graph
    graph = dcc.Graph(
        id="portfolio-trend-graph",
        figure=create_portfolio_trend_graph("1M"),
        config={'displayModeBar': False}
    )

    # Create summary table
    table_rows = []
    for acc in account_data:
        gain_class = "positive" if acc['gain_loss'] >= 0 else "negative"
        gain_str = f"+${acc['gain_loss']:,.2f}" if acc['gain_loss'] >= 0 else f"-${abs(acc['gain_loss']):,.2f}"
        pct_str = f"+{acc['gain_pct']:.1f}%" if acc['gain_pct'] >= 0 else f"{acc['gain_pct']:.1f}%"

        table_rows.append(html.Tr([
            html.Td(acc['name'], style={"fontWeight": "500", "textAlign": "left", "padding": "8px 0"}),
            html.Td(f"${acc['value']:,.2f}", style={"textAlign": "right", "padding": "8px 0"}),
            html.Td(html.Span(f"{gain_str} ({pct_str})", className=gain_class), style={"textAlign": "right", "padding": "8px 0"})
        ]))

    # Total row
    total_class = "positive" if total_gain >= 0 else "negative"
    total_gain_str = f"+${total_gain:,.2f}" if total_gain >= 0 else f"-${abs(total_gain):,.2f}"
    total_pct_str = f"+{total_pct:.1f}%" if total_pct >= 0 else f"{total_pct:.1f}%"

    summary_table = html.Table([
        html.Thead(html.Tr([
            html.Th("Account", style={"textAlign": "left", "paddingBottom": "8px", "color": "#666", "fontWeight": "600"}),
            html.Th("Value", style={"textAlign": "right", "paddingBottom": "8px", "color": "#666", "fontWeight": "600"}),
            html.Th("Gain/Loss", style={"textAlign": "right", "paddingBottom": "8px", "color": "#666", "fontWeight": "600"})
        ])),
        html.Tbody(table_rows),
        html.Tfoot(html.Tr([
            html.Td("Total", style={"fontWeight": "700", "paddingTop": "10px", "borderTop": "2px solid #e3f2fd", "textAlign": "left"}),
            html.Td(f"${total_value:,.2f}", style={"fontWeight": "700", "paddingTop": "10px", "borderTop": "2px solid #e3f2fd", "textAlign": "right"}),
            html.Td(html.Span(f"{total_gain_str} ({total_pct_str})", className=total_class),
                   style={"fontWeight": "700", "paddingTop": "10px", "borderTop": "2px solid #e3f2fd", "textAlign": "right"})
        ]))
    ], style={"width": "100%", "fontSize": "0.9rem"})

    return html.Div([
        time_buttons,
        graph,
        html.Div(style={"height": "15px"}),
        summary_table
    ])

def create_landing_page():
    """Create the main landing page"""
    return html.Div([
        dbc.Row([
            # Left Column - Watchlist
            dbc.Col([
                html.Div([
                    # Watchlist button/header
                    html.A([
                        html.Div("Watchlist", className="nav-card-header", style={"marginBottom": "0"})
                    ], href="/watchlist", style={"textDecoration": "none"}),
                    # Watchlist table directly below
                    html.Div([
                        html.Div(id="watchlist-preview-container")
                    ], style={"padding": "15px", "paddingTop": "10px"})
                ], className="stock-card", style={"overflow": "hidden"})
            ], width=6),

            # Right Column - Search & Portfolio
            dbc.Col([
                dbc.Row([
                    dbc.Col([
                        html.A([
                            html.Div([
                                html.Div("Search Stock", className="nav-card-header"),
                                html.P("Analyze any stock with detailed financials",
                                      style={"color": "#666", "margin": "0", "fontSize": "0.9rem"})
                            ])
                        ], href="/search", className="nav-card")
                    ], width=12)
                ], style={"marginBottom": "20px"}),
                dbc.Row([
                    dbc.Col([
                        html.A([
                            html.Div([
                                html.Div("Portfolio Management", className="nav-card-header"),
                                html.P("Track your investments and returns",
                                      style={"color": "#666", "margin": "0", "fontSize": "0.9rem"})
                            ])
                        ], href="/portfolio", className="nav-card")
                    ], width=12)
                ], style={"marginBottom": "20px"}),
                html.Div([
                    html.H5("Portfolio Summary", className="section-title", style={"marginTop": "0"}),
                    # Portfolio Filters
                    dbc.Row([
                        dbc.Col([
                            dcc.Dropdown(id="portfolio-filter-account",
                                        placeholder="Filter by Account...",
                                        style={"fontSize": "0.85rem"})
                        ], width=4),
                        dbc.Col([
                            dbc.Input(id="portfolio-filter-ticker", placeholder="Filter by Ticker...",
                                     className="add-input", style={"fontSize": "0.85rem", "height": "38px"})
                        ], width=4),
                        dbc.Col([
                            dbc.Input(id="portfolio-filter-date", type="date",
                                     className="add-input", style={"fontSize": "0.85rem", "height": "38px"})
                        ], width=4),
                    ], style={"marginBottom": "15px"}),
                    html.Div(id="portfolio-summary-container")
                ], className="stock-card", style={"padding": "20px"})
            ], width=6)
        ])
    ])

# ============================================================================
# FULL PAGE COMPONENTS
# ============================================================================

def create_watchlist_page():
    """Create full watchlist management page"""
    return html.Div([
        html.Div([
            html.H4("Manage Watchlist", className="section-title", style={"marginTop": "0"}),
            dbc.Row([
                dbc.Col([
                    dbc.Input(id="watchlist-add-input", placeholder="Enter ticker (e.g., AAPL)",
                             className="add-input")
                ], width=8),
                dbc.Col([
                    dbc.Button("Add to Watchlist", id="watchlist-add-btn", className="add-btn",
                              style={"width": "100%"})
                ], width=4)
            ], style={"marginBottom": "20px"}),
            html.Div(id="watchlist-full-container")
        ], className="stock-card", style={"padding": "25px"})
    ])

def create_portfolio_page():
    """Create full portfolio management page with graph, filters, and holdings"""
    portfolio = load_portfolio()
    accounts = portfolio.get("accounts", [])

    # Build filter options
    account_options = [{"label": "All Accounts", "value": "ALL"}] + \
                      [{"label": acc["name"], "value": acc["id"]} for acc in accounts]

    # Get all unique tickers
    all_tickers = set()
    for acc in accounts:
        for h in acc.get("holdings", []):
            all_tickers.add(h["ticker"])
    ticker_options = [{"label": "All Tickers", "value": "ALL"}] + \
                     [{"label": t, "value": t} for t in sorted(all_tickers)]

    return html.Div([
        # Portfolio Overview with Graph
        html.Div([
            html.H4("Portfolio Overview", className="section-title", style={"marginTop": "0"}),
            # Filters Row
            dbc.Row([
                dbc.Col([
                    dbc.Label("Account", style={"fontSize": "0.85rem", "fontWeight": "500"}),
                    dcc.Dropdown(id="portfolio-page-filter-account", options=account_options,
                                value="ALL", clearable=False,
                                style={"fontSize": "0.85rem"})
                ], width=3),
                dbc.Col([
                    dbc.Label("Ticker", style={"fontSize": "0.85rem", "fontWeight": "500"}),
                    dcc.Dropdown(id="portfolio-page-filter-ticker", options=ticker_options,
                                value="ALL", clearable=False, searchable=True,
                                placeholder="Search ticker...",
                                style={"fontSize": "0.85rem"})
                ], width=3),
                dbc.Col([
                    dbc.Label("Time Period", style={"fontSize": "0.85rem", "fontWeight": "500"}),
                    dbc.ButtonGroup([
                        dbc.Button("1D", id="port-time-1d", color="primary", outline=True, size="sm"),
                        dbc.Button("1W", id="port-time-1w", color="primary", outline=True, size="sm"),
                        dbc.Button("1M", id="port-time-1m", color="primary", size="sm"),
                        dbc.Button("3M", id="port-time-3m", color="primary", outline=True, size="sm"),
                        dbc.Button("6M", id="port-time-6m", color="primary", outline=True, size="sm"),
                        dbc.Button("1Y", id="port-time-1y", color="primary", outline=True, size="sm"),
                        dbc.Button("All", id="port-time-all", color="primary", outline=True, size="sm"),
                    ], size="sm", style={"marginTop": "5px"})
                ], width=6),
            ], style={"marginBottom": "20px"}),
            # Large Graph
            dcc.Graph(id="portfolio-page-graph", config={'displayModeBar': False},
                     style={"height": "350px"}),
            # Summary Stats
            html.Div(id="portfolio-page-summary", style={"marginTop": "15px"})
        ], className="stock-card", style={"padding": "25px", "marginBottom": "25px"}),

        # Holdings Detail Table
        html.Div([
            html.H4("Holdings Detail", className="section-title", style={"marginTop": "0"}),
            html.Div(id="portfolio-page-holdings-table")
        ], className="stock-card", style={"padding": "25px", "marginBottom": "25px"}),

        # Add Account Section
        html.Div([
            html.H4("Manage Accounts", className="section-title", style={"marginTop": "0"}),
            dbc.Row([
                dbc.Col([
                    dbc.Input(id="account-add-input", placeholder="New account name (e.g., Roth IRA)",
                             className="add-input")
                ], width=8),
                dbc.Col([
                    dbc.Button("Add Account", id="account-add-btn", className="add-btn",
                              style={"width": "100%"})
                ], width=4)
            ], style={"marginBottom": "20px"}),
            html.Div(id="portfolio-accounts-container")
        ], className="stock-card", style={"padding": "25px"})
    ])

def create_search_page():
    """Create the search/analysis page (original functionality)"""
    return html.Div([
        html.Div([
            dbc.Row([
                dbc.Col([
                    dbc.InputGroup([
                        dbc.InputGroupText(
                            html.I(className="fas fa-search"),
                            style={"backgroundColor": "white", "border": "2px solid #e3f2fd",
                                  "borderRight": "none", "borderRadius": "25px 0 0 25px"}
                        ),
                        dbc.Input(
                            id="ticker-input",
                            type="text",
                            value="",
                            placeholder="Search by ticker (e.g., AAPL, MSFT)...",
                            className="search-input",
                            style={"borderLeft": "none", "borderRadius": "0 25px 25px 0"}
                        ),
                    ], style={"maxWidth": "600px"}),
                ], width=8, className="d-flex justify-content-center"),
                dbc.Col([
                    dbc.Button("Analyze", id="run-button", className="search-btn", n_clicks=0)
                ], width=4, className="d-flex justify-content-start align-items-center"),
            ], className="justify-content-center align-items-center"),
        ], className="search-container"),
        dcc.Loading(
            id="loading",
            type="circle",
            color="#1a73e8",
            children=html.Div(id="results-container")
        )
    ])

def create_trades_page():
    """Create trade history page"""
    portfolio = load_portfolio()
    accounts = portfolio.get("accounts", [])
    account_options = [{"label": acc["name"], "value": acc["id"]} for acc in accounts]

    return html.Div([
        # Add Trade Section
        html.Div([
            html.H4("Record Trade", className="section-title", style={"marginTop": "0"}),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Account", style={"fontWeight": "500", "fontSize": "0.9rem"}),
                    dcc.Dropdown(id="trade-account", options=account_options,
                                placeholder="Select account...",
                                style={"marginBottom": "10px"})
                ], width=3),
                dbc.Col([
                    dbc.Label("Date", style={"fontWeight": "500", "fontSize": "0.9rem"}),
                    dbc.Input(id="trade-date", type="date",
                             value=datetime.now().strftime("%Y-%m-%d"),
                             className="add-input", style={"marginBottom": "10px"})
                ], width=2),
                dbc.Col([
                    dbc.Label("Action", style={"fontWeight": "500", "fontSize": "0.9rem"}),
                    dcc.Dropdown(id="trade-action",
                                options=[{"label": "BUY", "value": "BUY"},
                                        {"label": "SELL", "value": "SELL"}],
                                placeholder="Buy/Sell",
                                style={"marginBottom": "10px"})
                ], width=2),
                dbc.Col([
                    dbc.Label("Ticker", style={"fontWeight": "500", "fontSize": "0.9rem"}),
                    dbc.Input(id="trade-ticker", placeholder="AAPL",
                             className="add-input", style={"marginBottom": "10px"})
                ], width=2),
                dbc.Col([
                    dbc.Label("Shares", style={"fontWeight": "500", "fontSize": "0.9rem"}),
                    dbc.Input(id="trade-shares", type="number", placeholder="10",
                             className="add-input", style={"marginBottom": "10px"})
                ], width=1),
                dbc.Col([
                    dbc.Label("Price", style={"fontWeight": "500", "fontSize": "0.9rem"}),
                    dbc.Input(id="trade-price", type="number", placeholder="150.00",
                             className="add-input", style={"marginBottom": "10px"})
                ], width=2),
            ]),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Fees", style={"fontWeight": "500", "fontSize": "0.9rem"}),
                    dbc.Input(id="trade-fees", type="number", placeholder="0.00", value="0",
                             className="add-input")
                ], width=2),
                dbc.Col([
                    dbc.Label("Notes (optional)", style={"fontWeight": "500", "fontSize": "0.9rem"}),
                    dbc.Input(id="trade-notes", placeholder="Optional notes...",
                             className="add-input")
                ], width=6),
                dbc.Col([
                    dbc.Label(" ", style={"display": "block"}),
                    dbc.Button("Add Trade", id="trade-add-btn", className="add-btn",
                              style={"width": "100%"})
                ], width=4, style={"display": "flex", "alignItems": "flex-end"}),
            ], style={"marginTop": "10px"}),
        ], className="stock-card", style={"padding": "25px", "marginBottom": "25px"}),

        # CSV Import Section
        html.Div([
            html.H4("Import Holdings from CSV", className="section-title", style={"marginTop": "0"}),
            html.P("Upload a CSV with columns: Investment Account, Type, Company/Stock, Ticker, Amount of Stock",
                  style={"color": "#666", "fontSize": "0.85rem", "marginBottom": "15px"}),
            dbc.Row([
                dbc.Col([
                    dcc.Upload(
                        id='trades-csv-upload',
                        children=html.Div([
                            html.I(className="fas fa-cloud-upload-alt", style={"fontSize": "2rem", "color": "#1a73e8", "marginBottom": "10px"}),
                            html.Div("Drag & Drop or Click to Upload CSV"),
                        ], style={"textAlign": "center", "padding": "30px"}),
                        style={
                            'width': '100%',
                            'borderWidth': '2px',
                            'borderStyle': 'dashed',
                            'borderRadius': '10px',
                            'borderColor': '#1a73e8',
                            'backgroundColor': '#f8fbff',
                            'cursor': 'pointer'
                        },
                        multiple=False
                    )
                ], width=8),
                dbc.Col([
                    html.Div([
                        html.P("Expected Format:", style={"fontWeight": "600", "marginBottom": "5px"}),
                        html.Code("Investment Account,Type,Company/Stock,Ticker,Amount",
                                 style={"fontSize": "0.75rem", "display": "block", "padding": "10px",
                                       "backgroundColor": "#f5f5f5", "borderRadius": "5px"})
                    ])
                ], width=4),
            ]),
            html.Div(id="trades-csv-preview", style={"marginTop": "20px"}),
            dcc.Store(id="trades-csv-data-store")
        ], className="stock-card", style={"padding": "25px", "marginBottom": "25px"}),

        # Trade History & Stats
        html.Div([
            html.H4("Trade History", className="section-title", style={"marginTop": "0"}),
            # Filters
            dbc.Row([
                dbc.Col([
                    dcc.Dropdown(id="trade-filter-account", options=[{"label": "All Accounts", "value": "ALL"}] + account_options,
                                value="ALL", placeholder="Filter by account...")
                ], width=3),
                dbc.Col([
                    dcc.Dropdown(id="trade-filter-action",
                                options=[{"label": "All Actions", "value": "ALL"},
                                        {"label": "Buys Only", "value": "BUY"},
                                        {"label": "Sells Only", "value": "SELL"}],
                                value="ALL", placeholder="Filter by action...")
                ], width=2),
                dbc.Col([
                    dbc.Input(id="trade-filter-ticker", placeholder="Filter by ticker...",
                             className="add-input")
                ], width=2),
            ], style={"marginBottom": "20px"}),
            html.Div(id="trades-container"),
            html.Hr(),
            html.H5("Realized Gains Summary", className="section-title"),
            html.Div(id="realized-gains-container")
        ], className="stock-card", style={"padding": "25px"})
    ])

def create_income_page():
    """Create income tracking page with recurring income, RSUs, and improved UI"""
    income_data = load_income()
    current_month = datetime.now().strftime("%Y-%m")

    # Get available months for filtering
    all_incomes = income_data.get('income', [])
    months = sorted(set(i.get('date', '')[:7] for i in all_incomes if i.get('date')), reverse=True)

    # Income type colors
    income_type_colors = {
        "SALARY": "#2e7d32",
        "DIVIDEND": "#1a73e8",
        "INTEREST": "#f57c00",
        "BONUS": "#9c27b0",
        "RSU": "#00bcd4",
        "OTHER": "#607d8b"
    }

    return html.Div([
        # Stores for state
        dcc.Store(id="income-selected-month", data=current_month),
        dcc.Store(id="income-refresh-trigger"),

        # Income Overview Card
        html.Div([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        dbc.Button(html.I(className="fas fa-chevron-left"),
                                  id="income-month-prev", color="link",
                                  style={"fontSize": "1.2rem", "padding": "5px 15px"}),
                        html.Span(id="income-month-display",
                                 style={"fontSize": "1.5rem", "fontWeight": "600", "margin": "0 15px", "color": "#2e7d32"}),
                        dbc.Button(html.I(className="fas fa-chevron-right"),
                                  id="income-month-next", color="link",
                                  style={"fontSize": "1.2rem", "padding": "5px 15px"}),
                    ], style={"display": "flex", "alignItems": "center"})
                ], width=4),
                dbc.Col([
                    html.Div([
                        html.Span("This Month", style={"fontSize": "0.85rem", "color": "#666", "display": "block"}),
                        html.H3(id="income-this-month-total", style={"margin": "0", "color": "#2e7d32", "fontWeight": "700"})
                    ], style={"textAlign": "center"})
                ], width=2),
                dbc.Col([
                    html.Div([
                        html.Span("Year to Date", style={"fontSize": "0.85rem", "color": "#666", "display": "block"}),
                        html.H3(id="income-ytd-total", style={"margin": "0", "color": "#1a73e8", "fontWeight": "700"})
                    ], style={"textAlign": "center"})
                ], width=2),
                dbc.Col([
                    html.Div([
                        html.Span("RSU Value", style={"fontSize": "0.85rem", "color": "#666", "display": "block"}),
                        html.H3(id="income-rsu-value", style={"margin": "0", "color": "#00bcd4", "fontWeight": "700"})
                    ], style={"textAlign": "center"})
                ], width=2),
                dbc.Col([
                    html.Div([
                        html.Span("vs Last Month", style={"fontSize": "0.85rem", "color": "#666", "display": "block"}),
                        html.H3(id="income-vs-last-month", style={"margin": "0", "fontWeight": "700"})
                    ], style={"textAlign": "center"})
                ], width=2),
            ], style={"alignItems": "center"}),
        ], className="stock-card", style={"padding": "25px", "marginBottom": "25px"}),

        # Charts Row
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H4("Income by Type", className="section-title", style={"marginTop": "0"}),
                    dcc.Graph(id="income-pie-chart", config={'displayModeBar': False},
                             style={"height": "280px"})
                ], className="stock-card", style={"padding": "25px", "height": "100%"})
            ], width=5),
            dbc.Col([
                html.Div([
                    html.H4("Monthly Income Trend", className="section-title", style={"marginTop": "0"}),
                    dcc.Graph(id="income-trend-chart", config={'displayModeBar': False},
                             style={"height": "280px"})
                ], className="stock-card", style={"padding": "25px", "height": "100%"})
            ], width=7),
        ], style={"marginBottom": "25px"}),

        # Input Tabs: One-time, Recurring, RSUs
        html.Div([
            dbc.Tabs([
                dbc.Tab(label="+ Add Income", tab_id="tab-add-income",
                       label_style={"fontWeight": "600"}, active_label_style={"color": "#2e7d32"}),
                dbc.Tab(label="Recurring Income", tab_id="tab-recurring",
                       label_style={"fontWeight": "600"}, active_label_style={"color": "#2e7d32"}),
                dbc.Tab(label="RSU / Stock Comp", tab_id="tab-rsu",
                       label_style={"fontWeight": "600"}, active_label_style={"color": "#2e7d32"}),
            ], id="income-input-tabs", active_tab="tab-add-income", style={"marginBottom": "20px"}),

            # One-time Income Form
            html.Div([
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Date", style={"fontWeight": "500", "fontSize": "0.9rem"}),
                        dbc.Input(id="income-date", type="date",
                                 value=datetime.now().strftime("%Y-%m-%d"),
                                 className="add-input")
                    ], width=2),
                    dbc.Col([
                        dbc.Label("Type", style={"fontWeight": "500", "fontSize": "0.9rem"}),
                        dcc.Dropdown(id="income-type",
                                    options=[{"label": "Salary", "value": "SALARY"},
                                            {"label": "Dividend", "value": "DIVIDEND"},
                                            {"label": "Interest", "value": "INTEREST"},
                                            {"label": "Bonus", "value": "BONUS"},
                                            {"label": "RSU Vesting", "value": "RSU"},
                                            {"label": "Other", "value": "OTHER"}],
                                    placeholder="Income type...")
                    ], width=2),
                    dbc.Col([
                        dbc.Label("Source", style={"fontWeight": "500", "fontSize": "0.9rem"}),
                        dbc.Input(id="income-source", placeholder="Employer/Stock/Bank",
                                 className="add-input")
                    ], width=3),
                    dbc.Col([
                        dbc.Label("Amount ($)", style={"fontWeight": "500", "fontSize": "0.9rem"}),
                        dbc.Input(id="income-amount", type="number", placeholder="5000.00",
                                 className="add-input", step="0.01")
                    ], width=2),
                    dbc.Col([
                        dbc.Label(" ", style={"display": "block"}),
                        dbc.Button("Add Income", id="income-add-btn", className="add-btn",
                                  style={"width": "100%"})
                    ], width=3, style={"display": "flex", "alignItems": "flex-end"}),
                ]),
            ], id="income-onetime-form"),

            # Recurring Income Form
            html.Div([
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Description", style={"fontWeight": "500", "fontSize": "0.9rem"}),
                        dbc.Input(id="recurring-desc", placeholder="e.g., Biweekly Salary",
                                 className="add-input")
                    ], width=3),
                    dbc.Col([
                        dbc.Label("Amount ($)", style={"fontWeight": "500", "fontSize": "0.9rem"}),
                        dbc.Input(id="recurring-amount", type="number", placeholder="3000.00",
                                 className="add-input", step="0.01")
                    ], width=2),
                    dbc.Col([
                        dbc.Label("Every X Weeks", style={"fontWeight": "500", "fontSize": "0.9rem"}),
                        dcc.Dropdown(id="recurring-weeks",
                                    options=[{"label": "Weekly (1)", "value": 1},
                                            {"label": "Biweekly (2)", "value": 2},
                                            {"label": "Monthly (4)", "value": 4},
                                            {"label": "Bimonthly (8)", "value": 8}],
                                    value=2, clearable=False)
                    ], width=2),
                    dbc.Col([
                        dbc.Label("Start Date", style={"fontWeight": "500", "fontSize": "0.9rem"}),
                        dbc.Input(id="recurring-start", type="date",
                                 value=datetime.now().strftime("%Y-%m-%d"),
                                 className="add-input")
                    ], width=2),
                    dbc.Col([
                        dbc.Label(" ", style={"display": "block"}),
                        dbc.Button("Add Recurring", id="recurring-add-btn", className="add-btn",
                                  style={"width": "100%"})
                    ], width=3, style={"display": "flex", "alignItems": "flex-end"}),
                ]),
                html.Hr(style={"margin": "20px 0"}),
                html.H5("Active Recurring Income", style={"marginBottom": "15px", "color": "#666"}),
                html.Div(id="recurring-income-list")
            ], id="income-recurring-form", style={"display": "none"}),

            # RSU Form
            html.Div([
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Company Ticker", style={"fontWeight": "500", "fontSize": "0.9rem"}),
                        dbc.Input(id="rsu-ticker", placeholder="e.g., AAPL",
                                 className="add-input", style={"textTransform": "uppercase"})
                    ], width=2),
                    dbc.Col([
                        dbc.Label("Shares Owned", style={"fontWeight": "500", "fontSize": "0.9rem"}),
                        dbc.Input(id="rsu-shares", type="number", placeholder="100",
                                 className="add-input", step="0.01")
                    ], width=2),
                    dbc.Col([
                        dbc.Label("Vest Date", style={"fontWeight": "500", "fontSize": "0.9rem"}),
                        dbc.Input(id="rsu-vest-date", type="date",
                                 value=datetime.now().strftime("%Y-%m-%d"),
                                 className="add-input")
                    ], width=2),
                    dbc.Col([
                        dbc.Label("Grant Price ($)", style={"fontWeight": "500", "fontSize": "0.9rem"}),
                        dbc.Input(id="rsu-grant-price", type="number", placeholder="150.00",
                                 className="add-input", step="0.01")
                    ], width=2),
                    dbc.Col([
                        dbc.Label(" ", style={"display": "block"}),
                        dbc.Button("Add RSU", id="rsu-add-btn", className="add-btn",
                                  style={"width": "100%"})
                    ], width=2, style={"display": "flex", "alignItems": "flex-end"}),
                    dbc.Col([
                        dbc.Label(" ", style={"display": "block"}),
                        dbc.Button("Refresh Prices", id="rsu-refresh-btn", color="secondary",
                                  style={"width": "100%"})
                    ], width=2, style={"display": "flex", "alignItems": "flex-end"}),
                ]),
                html.Hr(style={"margin": "20px 0"}),
                html.H5("RSU Holdings", style={"marginBottom": "15px", "color": "#666"}),
                html.Div(id="rsu-holdings-list")
            ], id="income-rsu-form", style={"display": "none"}),

        ], className="stock-card", style={"padding": "25px", "marginBottom": "25px"}),

        # Income History
        html.Div([
            html.H4("Income History", className="section-title", style={"marginTop": "0"}),
            dbc.Row([
                dbc.Col([
                    dcc.Dropdown(id="income-filter-month",
                                options=[{"label": "All Months", "value": "ALL"}] +
                                        [{"label": datetime.strptime(m, "%Y-%m").strftime("%B %Y"), "value": m}
                                         for m in months[:24]],
                                value="ALL", placeholder="Filter by month...")
                ], width=3),
                dbc.Col([
                    dcc.Dropdown(id="income-filter-type",
                                options=[{"label": "All Types", "value": "ALL"},
                                        {"label": "Salary", "value": "SALARY"},
                                        {"label": "Dividend", "value": "DIVIDEND"},
                                        {"label": "Interest", "value": "INTEREST"},
                                        {"label": "Bonus", "value": "BONUS"},
                                        {"label": "RSU", "value": "RSU"},
                                        {"label": "Other", "value": "OTHER"}],
                                value="ALL", placeholder="Filter by type...")
                ], width=2),
                dbc.Col([
                    dbc.Input(id="income-filter-search", placeholder="Search source...",
                             className="add-input")
                ], width=3),
                dbc.Col([
                    html.Div(id="income-count-display",
                            style={"textAlign": "right", "color": "#666", "fontSize": "0.9rem", "paddingTop": "8px"})
                ], width=4),
            ], style={"marginBottom": "20px"}),
            html.Div(id="income-history-container"),
            # Summary by month
            html.Hr(style={"margin": "25px 0"}),
            html.H5("Monthly Summary", style={"marginBottom": "15px", "color": "#666"}),
            html.Div(id="income-monthly-summary")
        ], className="stock-card", style={"padding": "25px"})
    ])

def create_expenses_page():
    """Create expense tracking page with Budget vs Actuals, CSV import, and full editing"""
    expenses_data = load_expenses()
    categories = expenses_data.get("categories", ["Dining", "Shopping", "Gas", "Entertainment", "Bills", "Travel", "Subscriptions", "Other"])

    # Get current month for default display
    current_month = datetime.now().strftime("%Y-%m")

    # Category colors for consistent styling
    category_colors = {
        "Dining": "#FF6B6B",
        "Shopping": "#4ECDC4",
        "Gas": "#45B7D1",
        "Entertainment": "#96CEB4",
        "Bills": "#FFEAA7",
        "Travel": "#DDA0DD",
        "Subscriptions": "#98D8C8",
        "Other": "#C9C9C9"
    }

    return html.Div([
        # Hidden stores for state management
        dcc.Store(id="expense-selected-month", data=current_month),
        dcc.Store(id="expense-csv-data-store"),
        dcc.Store(id="expense-edit-mode-store", data=None),

        # Monthly Overview Card
        html.Div([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        dbc.Button(html.I(className="fas fa-chevron-left"),
                                  id="expense-month-prev", color="link",
                                  style={"fontSize": "1.2rem", "padding": "5px 15px"}),
                        html.Span(id="expense-month-display",
                                 style={"fontSize": "1.5rem", "fontWeight": "600", "margin": "0 15px", "color": "#1a73e8"}),
                        dbc.Button(html.I(className="fas fa-chevron-right"),
                                  id="expense-month-next", color="link",
                                  style={"fontSize": "1.2rem", "padding": "5px 15px"}),
                    ], style={"display": "flex", "alignItems": "center"})
                ], width=4),
                dbc.Col([
                    html.Div([
                        html.Div([
                            html.Span("Total Spent", style={"fontSize": "0.85rem", "color": "#666"}),
                            html.H3(id="expense-total-spent", style={"margin": "0", "color": "#dc3545", "fontWeight": "700"})
                        ], style={"textAlign": "center", "padding": "0 30px", "borderRight": "1px solid #eee"}),
                    ], style={"display": "inline-block"})
                ], width=3, style={"display": "flex", "justifyContent": "center"}),
                dbc.Col([
                    html.Div([
                        html.Span("vs Budget", style={"fontSize": "0.85rem", "color": "#666"}),
                        html.H3(id="expense-vs-budget", style={"margin": "0", "fontWeight": "700"})
                    ], style={"textAlign": "center"})
                ], width=2, style={"display": "flex", "justifyContent": "center", "alignItems": "center"}),
                dbc.Col([
                    html.Div([
                        html.Span("vs Last Month", style={"fontSize": "0.85rem", "color": "#666"}),
                        html.H3(id="expense-vs-last-month", style={"margin": "0", "fontWeight": "700"})
                    ], style={"textAlign": "center"})
                ], width=3, style={"display": "flex", "justifyContent": "center", "alignItems": "center"}),
            ], style={"alignItems": "center"}),
            html.Hr(style={"margin": "20px 0"}),
            # Quick category breakdown
            html.Div(id="expense-category-pills", style={"display": "flex", "flexWrap": "wrap", "gap": "10px"})
        ], className="stock-card", style={"padding": "25px", "marginBottom": "25px"}),

        # Budget vs Actuals Card
        html.Div([
            dbc.Row([
                dbc.Col([
                    html.H4("Budget vs Actuals", className="section-title", style={"marginTop": "0", "marginBottom": "0"})
                ], width=6),
                dbc.Col([
                    html.Div([
                        dcc.Dropdown(
                            id="budget-month-selector",
                            options=[],  # Populated by callback
                            value=current_month,
                            style={"width": "180px", "display": "inline-block", "marginRight": "10px"},
                            clearable=False
                        ),
                        dbc.Button("Copy from Previous", id="budget-copy-prev-btn", color="secondary", size="sm",
                                  style={"marginRight": "10px"}),
                        dbc.Button("Set All Budgets", id="budget-set-all-btn", color="primary", size="sm"),
                    ], style={"display": "flex", "alignItems": "center", "justifyContent": "flex-end"})
                ], width=6),
            ], style={"marginBottom": "20px"}),
            html.Div(id="budget-progress-container")
        ], className="stock-card", style={"padding": "25px", "marginBottom": "25px"}),

        # Analytics Row
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H4("Spending by Category", className="section-title", style={"marginTop": "0"}),
                    dcc.Graph(id="expense-pie-chart", config={'displayModeBar': False},
                             style={"height": "300px"})
                ], className="stock-card", style={"padding": "25px", "height": "100%"})
            ], width=6),
            dbc.Col([
                html.Div([
                    html.H4("Monthly Trend", className="section-title", style={"marginTop": "0"}),
                    dcc.Graph(id="expense-bar-chart", config={'displayModeBar': False},
                             style={"height": "300px"})
                ], className="stock-card", style={"padding": "25px", "height": "100%"})
            ], width=6),
        ], style={"marginBottom": "25px"}),

        # Add Expense / Import CSV Card
        html.Div([
            dbc.Tabs([
                dbc.Tab(label="+ Add Expense", tab_id="tab-add-expense",
                       label_style={"fontWeight": "600"}, active_label_style={"color": "#1a73e8"}),
                dbc.Tab(label="Import CSV", tab_id="tab-import-csv",
                       label_style={"fontWeight": "600"}, active_label_style={"color": "#1a73e8"}),
            ], id="expense-input-tabs", active_tab="tab-add-expense", style={"marginBottom": "20px"}),

            # Add Expense Form (shown by default)
            html.Div([
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Date", style={"fontWeight": "500", "fontSize": "0.9rem"}),
                        dbc.Input(id="expense-date", type="date",
                                 value=datetime.now().strftime("%Y-%m-%d"),
                                 className="add-input")
                    ], width=2),
                    dbc.Col([
                        dbc.Label("Description", style={"fontWeight": "500", "fontSize": "0.9rem"}),
                        dbc.Input(id="expense-desc", placeholder="Store/Merchant name",
                                 className="add-input")
                    ], width=3),
                    dbc.Col([
                        dbc.Label("Amount ($)", style={"fontWeight": "500", "fontSize": "0.9rem"}),
                        dbc.Input(id="expense-amount", type="number", placeholder="50.00",
                                 className="add-input", step="0.01")
                    ], width=2),
                    dbc.Col([
                        dbc.Label("Category", style={"fontWeight": "500", "fontSize": "0.9rem"}),
                        dcc.Dropdown(id="expense-category",
                                    options=[{"label": c, "value": c} for c in categories],
                                    placeholder="Select category...")
                    ], width=2),
                    dbc.Col([
                        dbc.Label(" ", style={"display": "block"}),
                        dbc.Button("Add Expense", id="expense-add-btn", className="add-btn",
                                  style={"width": "100%"})
                    ], width=3, style={"display": "flex", "alignItems": "flex-end"}),
                ]),
            ], id="add-expense-form"),

            # CSV Import Section (hidden by default, shown via callback)
            html.Div([
                dbc.Row([
                    dbc.Col([
                        dcc.Upload(
                            id="expense-csv-upload",
                            children=html.Div([
                                html.I(className="fas fa-cloud-upload-alt",
                                      style={"fontSize": "2.5rem", "color": "#1a73e8", "marginBottom": "10px"}),
                                html.Div("Drag & Drop or Click to Upload CSV"),
                                html.Div("Supports Capital One, Chase, and other bank formats",
                                        style={"fontSize": "0.8rem", "color": "#888", "marginTop": "5px"})
                            ], style={"textAlign": "center", "padding": "30px"}),
                            style={
                                'width': '100%',
                                'borderWidth': '2px',
                                'borderStyle': 'dashed',
                                'borderRadius': '15px',
                                'borderColor': '#1a73e8',
                                'backgroundColor': '#f8fbff',
                                'cursor': 'pointer'
                            },
                            multiple=False
                        )
                    ], width=12),
                ]),
                html.Div(id="expense-csv-preview", style={"marginTop": "20px"})
            ], id="import-csv-form", style={"display": "none"}),
        ], className="stock-card", style={"padding": "25px", "marginBottom": "25px"}),

        # Transaction History Card
        html.Div([
            html.H4("Transaction History", className="section-title", style={"marginTop": "0"}),
            dbc.Row([
                dbc.Col([
                    dcc.Dropdown(id="expense-filter-month",
                                options=[{"label": "All Months", "value": "ALL"}],  # Populated by callback
                                value="ALL", placeholder="Filter by month...",
                                style={"width": "100%"})
                ], width=2),
                dbc.Col([
                    dcc.Dropdown(id="expense-filter-category",
                                options=[{"label": "All Categories", "value": "ALL"}] +
                                        [{"label": c, "value": c} for c in categories],
                                value="ALL", placeholder="Filter by category...",
                                multi=True)
                ], width=3),
                dbc.Col([
                    dbc.Input(id="expense-filter-search", placeholder="Search description...",
                             className="add-input")
                ], width=3),
                dbc.Col([
                    dcc.Dropdown(id="expense-sort-by",
                                options=[
                                    {"label": "Date (Newest)", "value": "date-desc"},
                                    {"label": "Date (Oldest)", "value": "date-asc"},
                                    {"label": "Amount (High to Low)", "value": "amount-desc"},
                                    {"label": "Amount (Low to High)", "value": "amount-asc"},
                                    {"label": "Category", "value": "category"}
                                ],
                                value="date-desc", clearable=False)
                ], width=2),
                dbc.Col([
                    html.Div(id="expense-count-display",
                            style={"textAlign": "right", "color": "#666", "fontSize": "0.9rem", "paddingTop": "8px"})
                ], width=2),
            ], style={"marginBottom": "20px"}),
            html.Div(id="expense-history-container"),
            # Store for tracking which row is being edited
            dcc.Store(id="expense-editing-row-id", data=None),
        ], className="stock-card", style={"padding": "25px"}),

        # Hidden div for triggering refreshes
        html.Div(id="expense-refresh-trigger", style={"display": "none"})
    ])

def create_analytics_page():
    """Create portfolio analytics page - streamlined"""
    return html.Div([
        # Top Row: Allocation + Performance
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H5("Current Allocation", className="section-title", style={"marginTop": "0", "marginBottom": "10px"}),
                    dcc.Graph(id="allocation-pie-chart", config={'displayModeBar': False},
                             style={"height": "280px"})
                ], className="stock-card", style={"padding": "20px"})
            ], width=4),
            dbc.Col([
                html.Div([
                    html.H5("Target vs Actual", className="section-title", style={"marginTop": "0", "marginBottom": "10px"}),
                    dcc.Graph(id="target-vs-actual-chart", config={'displayModeBar': False},
                             style={"height": "280px"})
                ], className="stock-card", style={"padding": "20px"})
            ], width=4),
            dbc.Col([
                html.Div([
                    html.H5("Performance", className="section-title", style={"marginTop": "0", "marginBottom": "10px"}),
                    html.Div(id="performance-metrics-container")
                ], className="stock-card", style={"padding": "20px", "height": "100%"})
            ], width=4),
        ], style={"marginBottom": "20px"}),

        # Bottom Row: Rebalancing + Performers
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H5("Rebalancing Suggestions", className="section-title", style={"marginTop": "0", "marginBottom": "10px"}),
                    html.Div(id="rebalance-container")
                ], className="stock-card", style={"padding": "20px"})
            ], width=6),
            dbc.Col([
                html.Div([
                    dbc.Row([
                        dbc.Col([
                            html.H6("Top Performers", style={"color": "#2e7d32", "fontWeight": "600", "marginBottom": "10px"}),
                            html.Div(id="top-performers-container")
                        ], width=6),
                        dbc.Col([
                            html.H6("Bottom Performers", style={"color": "#dc3545", "fontWeight": "600", "marginBottom": "10px"}),
                            html.Div(id="bottom-performers-container")
                        ], width=6),
                    ])
                ], className="stock-card", style={"padding": "20px"})
            ], width=6),
        ]),
        # Hidden elements for callbacks that expect them
        html.Div(id="sector-pie-chart", style={"display": "none"})
    ])

def create_alerts_page():
    """Create price alerts page"""
    return html.Div([
        # Triggered Alerts Banner
        html.Div(id="triggered-alerts-banner"),

        # Create Alert Section
        html.Div([
            html.H4("Create Price Alert", className="section-title", style={"marginTop": "0"}),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Ticker", style={"fontWeight": "500", "fontSize": "0.9rem"}),
                    dbc.Input(id="alert-ticker", placeholder="AAPL",
                             className="add-input")
                ], width=2),
                dbc.Col([
                    dbc.Label("Condition", style={"fontWeight": "500", "fontSize": "0.9rem"}),
                    dcc.Dropdown(id="alert-condition",
                                options=[{"label": "Price Goes Above", "value": "ABOVE"},
                                        {"label": "Price Goes Below", "value": "BELOW"}],
                                placeholder="Select condition...")
                ], width=3),
                dbc.Col([
                    dbc.Label("Target Price", style={"fontWeight": "500", "fontSize": "0.9rem"}),
                    dbc.Input(id="alert-price", type="number", placeholder="200.00",
                             className="add-input")
                ], width=2),
                dbc.Col([
                    dbc.Label(" ", style={"display": "block"}),
                    dbc.Button("Create Alert", id="alert-add-btn", className="add-btn",
                              style={"width": "100%"})
                ], width=3, style={"display": "flex", "alignItems": "flex-end"}),
            ]),
        ], className="stock-card", style={"padding": "25px", "marginBottom": "25px"}),

        # Active Alerts
        html.Div([
            html.H4("Active Alerts", className="section-title", style={"marginTop": "0"}),
            html.Div(id="active-alerts-container")
        ], className="stock-card", style={"padding": "25px", "marginBottom": "25px"}),

        # Alert History
        html.Div([
            html.H4("Triggered Alert History", className="section-title", style={"marginTop": "0"}),
            html.Div(id="alert-history-container")
        ], className="stock-card", style={"padding": "25px"})
    ])

def create_settings_page():
    """Create settings page"""
    settings = load_settings()

    return html.Div([
        # Target Allocations
        html.Div([
            html.H4("Target Allocations", className="section-title", style={"marginTop": "0"}),
            html.P("Set your target allocation percentages for rebalancing suggestions.",
                  style={"color": "#666", "fontSize": "0.9rem"}),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Ticker", style={"fontWeight": "500", "fontSize": "0.9rem"}),
                    dbc.Input(id="target-ticker", placeholder="AAPL",
                             className="add-input")
                ], width=3),
                dbc.Col([
                    dbc.Label("Target %", style={"fontWeight": "500", "fontSize": "0.9rem"}),
                    dbc.Input(id="target-pct", type="number", placeholder="20",
                             className="add-input")
                ], width=2),
                dbc.Col([
                    dbc.Label(" ", style={"display": "block"}),
                    dbc.Button("Add Target", id="target-add-btn", className="add-btn",
                              style={"width": "100%"})
                ], width=3, style={"display": "flex", "alignItems": "flex-end"}),
            ], style={"marginBottom": "20px"}),
            html.Div(id="target-allocations-container")
        ], className="stock-card", style={"padding": "25px", "marginBottom": "25px"}),

        # Rebalance Threshold
        html.Div([
            html.H4("Rebalance Settings", className="section-title", style={"marginTop": "0"}),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Rebalance Threshold (%)", style={"fontWeight": "500", "fontSize": "0.9rem"}),
                    html.P("Suggest rebalancing when allocation differs from target by this percentage.",
                          style={"color": "#666", "fontSize": "0.8rem"}),
                    dbc.Input(id="rebalance-threshold", type="number",
                             value=settings.get("rebalance_threshold", 5),
                             className="add-input", style={"maxWidth": "200px"})
                ], width=6),
                dbc.Col([
                    dbc.Label(" ", style={"display": "block"}),
                    dbc.Button("Save Settings", id="save-settings-btn", className="add-btn")
                ], width=6, style={"display": "flex", "alignItems": "flex-end"}),
            ])
        ], className="stock-card", style={"padding": "25px", "marginBottom": "25px"}),

        # Category Management
        html.Div([
            html.H4("Expense Categories", className="section-title", style={"marginTop": "0"}),
            dbc.Row([
                dbc.Col([
                    dbc.Input(id="new-category", placeholder="New category name",
                             className="add-input")
                ], width=4),
                dbc.Col([
                    dbc.Button("Add Category", id="category-add-btn", className="add-btn")
                ], width=3),
            ], style={"marginBottom": "20px"}),
            html.Div(id="categories-container")
        ], className="stock-card", style={"padding": "25px"})
    ])

def create_finance_hub_page():
    """Create personal finance hub landing page"""
    income_data = load_income()
    expenses_data = load_expenses()

    # Calculate totals
    total_income = sum(i.get("amount", 0) for i in income_data.get("income", []))
    total_expenses = sum(e.get("amount", 0) for e in expenses_data.get("expenses", []))
    net_flow = total_income - total_expenses

    return html.Div([
        # Summary Cards
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H6("Total Income", style={"color": "#666", "marginBottom": "5px"}),
                    html.H3(f"${total_income:,.2f}", style={"color": "#2e7d32", "fontWeight": "700"})
                ], className="stock-card", style={"padding": "20px", "textAlign": "center"})
            ], width=3),
            dbc.Col([
                html.Div([
                    html.H6("Total Expenses", style={"color": "#666", "marginBottom": "5px"}),
                    html.H3(f"${total_expenses:,.2f}", style={"color": "#dc3545", "fontWeight": "700"})
                ], className="stock-card", style={"padding": "20px", "textAlign": "center"})
            ], width=3),
            dbc.Col([
                html.Div([
                    html.H6("Net Cash Flow", style={"color": "#666", "marginBottom": "5px"}),
                    html.H3(f"${net_flow:,.2f}",
                           style={"color": "#2e7d32" if net_flow >= 0 else "#dc3545", "fontWeight": "700"})
                ], className="stock-card", style={"padding": "20px", "textAlign": "center"})
            ], width=3),
            dbc.Col([
                html.Div([
                    html.H6("Available to Invest", style={"color": "#666", "marginBottom": "5px"}),
                    html.H3(f"${max(net_flow, 0):,.2f}",
                           style={"color": "#1a73e8", "fontWeight": "700"}),
                    html.P("From Net Cash Flow", style={"color": "#888", "fontSize": "0.75rem", "margin": "5px 0 0 0"})
                ], className="stock-card", style={"padding": "20px", "textAlign": "center",
                                                   "border": "2px solid #1a73e8" if net_flow > 0 else "none"})
            ], width=3),
        ], style={"marginBottom": "25px"}),

        # Quick Links
        dbc.Row([
            dbc.Col([
                html.A([
                    html.Div([
                        html.Div("Income Tracker", className="nav-card-header"),
                        html.P("Track salary, dividends, and other income",
                              style={"color": "#666", "margin": "0", "fontSize": "0.9rem"})
                    ])
                ], href="/finance/income", className="nav-card")
            ], width=6),
            dbc.Col([
                html.A([
                    html.Div([
                        html.Div("Expense Tracker", className="nav-card-header"),
                        html.P("Import credit card statements and track spending",
                              style={"color": "#666", "margin": "0", "fontSize": "0.9rem"})
                    ])
                ], href="/finance/expenses", className="nav-card")
            ], width=6),
        ])
    ])

# ============================================================================
# ANALYZE TICKER (Original)
# ============================================================================

def analyze_ticker(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        financials, cashflow, balance_sheet = get_aligned_data(ticker)

        if financials is None:
            return dbc.Alert(f"Skipping {ticker_symbol}: No financial data found.", color="danger", className="mb-3")

        info = ticker.info
        company_name = info.get('longName', info.get('shortName', ticker_symbol))
        f_info = ticker.fast_info
        hist = ticker.history(period="5y")

        # Use historical close for consistency (not real-time price)
        current_price = hist['Close'].iloc[-1] if not hist.empty else f_info.last_price
        current_date = hist.index[-1] if not hist.empty else datetime.now()

        def get_price_at_date(target_date):
            """Find price closest to target date (on or before)"""
            valid_dates = hist.index[hist.index <= target_date]
            if len(valid_dates) > 0:
                return hist.loc[valid_dates[-1], 'Close']
            return None

        def calc_pct(time_delta):
            """Calculate return from a time period ago"""
            target = current_date - time_delta
            past_price = get_price_at_date(target)
            if past_price is not None and past_price > 0:
                return ((current_price - past_price) / past_price) * 100
            return 0.0

        def format_pct(pct):
            if pct < 0:
                return f"({abs(pct):.2f}%)"
            return f"+{pct:.2f}%"

        pct_1d = calc_pct(timedelta(days=1))           # 1 calendar day
        pct_1w = calc_pct(timedelta(days=7))           # 7 calendar days
        pct_1m = calc_pct(relativedelta(months=1))     # Exactly 1 month
        pct_6m = calc_pct(relativedelta(months=6))     # Exactly 6 months
        pct_1y = calc_pct(relativedelta(years=1))      # Exactly 1 year

        market_data = [{
            "Metric": "Current Price",
            "Value": f"${current_price:.2f}",
            "1-Day": format_pct(pct_1d),
            "1-Week": format_pct(pct_1w),
            "1-Month": format_pct(pct_1m),
            "6-Month": format_pct(pct_6m),
            "1-Year": format_pct(pct_1y)
        }]
        market_columns = [
            {"name": "Metric", "id": "Metric"},
            {"name": "Value", "id": "Value"},
            {"name": "1-Day", "id": "1-Day"},
            {"name": "1-Week", "id": "1-Week"},
            {"name": "1-Month", "id": "1-Month"},
            {"name": "6-Month", "id": "6-Month"},
            {"name": "1-Year", "id": "1-Year"}
        ]

        try:
            d_e = balance_sheet.loc["Total Debt"].iloc[0] / balance_sheet.loc["Stockholders Equity"].iloc[0]
            d_e_str = f"{d_e:.2f}" if d_e >= 0 else f"({abs(d_e):.2f})"
        except:
            d_e_str = "N/A"

        market_cap_b = f_info.market_cap / 1e9
        ratios_data = [{
            "Metric": "Key Ratios",
            "PE Ratio (TTM)": str(info.get('trailingPE', 'N/A') if info.get('trailingPE') else 'N/A'),
            "EPS (TTM)": str(info.get('trailingEps', 'N/A') if info.get('trailingEps') else 'N/A'),
            "Debt to Equity": d_e_str,
            "Market Cap ($B)": f"{market_cap_b:,.1f}"
        }]
        ratios_columns = [
            {"name": "Metric", "id": "Metric"},
            {"name": "PE Ratio (TTM)", "id": "PE Ratio (TTM)"},
            {"name": "EPS (TTM)", "id": "EPS (TTM)"},
            {"name": "Debt to Equity", "id": "Debt to Equity"},
            {"name": "Market Cap ($B)", "id": "Market Cap ($B)"}
        ]

        peg = info.get('pegRatio', None)
        ps = info.get('priceToSalesTrailing12Months', None)
        pb = info.get('priceToBook', None)
        ev_ebitda = info.get('enterpriseToEbitda', None)

        valuation_data = [{
            "Metric": "Valuation",
            "PEG Ratio": f"{peg:.2f}" if peg else "N/A",
            "Price/Sales": f"{ps:.2f}" if ps else "N/A",
            "Price/Book": f"{pb:.2f}" if pb else "N/A",
            "EV/EBITDA": f"{ev_ebitda:.2f}" if ev_ebitda else "N/A"
        }]
        valuation_columns = [
            {"name": "Metric", "id": "Metric"},
            {"name": "PEG Ratio", "id": "PEG Ratio"},
            {"name": "Price/Sales", "id": "Price/Sales"},
            {"name": "Price/Book", "id": "Price/Book"},
            {"name": "EV/EBITDA", "id": "EV/EBITDA"}
        ]

        rev = financials.loc["Total Revenue"]
        net_inc = financials.loc["Net Income"]
        ebitda = financials.loc["EBITDA"] if "EBITDA" in financials.index else None

        rev_growth = ((rev.iloc[:4] - rev.iloc[1:5].values) / rev.iloc[1:5].values) * 100
        net_margin = (net_inc.iloc[:4] / rev.iloc[:4]) * 100
        rev_ttm = rev.iloc[:4].sum()

        fin_data = []
        metrics = ["Total Revenue ($B)", "Rev Growth %", "Net Income ($B)", "Net Margin %", "EBITDA ($B)"]
        for metric in metrics:
            row = {"Metric": metric}
            for i in range(4):
                col_name = str(rev.index[i])
                if metric == "Total Revenue ($B)":
                    val, is_neg = format_display_value(rev.iloc[i])
                    row[col_name] = val
                elif metric == "Rev Growth %":
                    g = rev_growth.iloc[i]
                    row[col_name] = f"({abs(g):.1f}%)" if g < 0 else f"+{g:.1f}%"
                elif metric == "Net Income ($B)":
                    val, is_neg = format_display_value(net_inc.iloc[i])
                    row[col_name] = val
                elif metric == "Net Margin %":
                    m = net_margin.iloc[i]
                    row[col_name] = f"({abs(m):.1f}%)" if m < 0 else f"{m:.1f}%"
                elif metric == "EBITDA ($B)":
                    if ebitda is not None:
                        val, is_neg = format_display_value(ebitda.iloc[i])
                        row[col_name] = val
                    else:
                        row[col_name] = "N/A"

            if metric == "Total Revenue ($B)":
                val, is_neg = format_display_value(rev_ttm)
                row["TTM"] = val
            elif metric == "Rev Growth %":
                ttm_growth = ((rev_ttm - rev.iloc[1:5].sum())/rev.iloc[1:5].sum()*100)
                row["TTM"] = f"({abs(ttm_growth):.1f}%)" if ttm_growth < 0 else f"+{ttm_growth:.1f}%"
            elif metric == "Net Income ($B)":
                val, is_neg = format_display_value(net_inc.iloc[:4].sum())
                row["TTM"] = val
            elif metric == "Net Margin %":
                m = (net_inc.iloc[:4].sum()/rev_ttm*100)
                row["TTM"] = f"({abs(m):.1f}%)" if m < 0 else f"{m:.1f}%"
            elif metric == "EBITDA ($B)":
                if ebitda is not None:
                    val, is_neg = format_display_value(ebitda.iloc[:4].sum())
                    row["TTM"] = val
                else:
                    row["TTM"] = "N/A"
            fin_data.append(row)

        fin_columns = [{"name": "Metric", "id": "Metric"}] + [{"name": str(rev.index[i]), "id": str(rev.index[i])} for i in range(4)] + [{"name": "TTM", "id": "TTM"}]

        ocf, capex = cashflow.loc["Operating Cash Flow"], cashflow.loc["Capital Expenditure"]
        cf_data = []
        for metric in ["Operating Cash Flow ($B)", "Capital Expenditure ($B)"]:
            row = {"Metric": metric}
            for i in range(4):
                col_name = str(ocf.index[i])
                if metric == "Operating Cash Flow ($B)":
                    val, is_neg = format_display_value(ocf.iloc[i])
                    row[col_name] = val
                else:
                    val, is_neg = format_display_value(capex.iloc[i])
                    row[col_name] = val
            if metric == "Operating Cash Flow ($B)":
                val, is_neg = format_display_value(ocf.iloc[:4].sum())
                row["TTM"] = val
            else:
                val, is_neg = format_display_value(capex.iloc[:4].sum())
                row["TTM"] = val
            cf_data.append(row)

        cf_columns = [{"name": "Metric", "id": "Metric"}] + [{"name": str(ocf.index[i]), "id": str(ocf.index[i])} for i in range(4)] + [{"name": "TTM", "id": "TTM"}]

        fcf_ttm = (ocf.iloc[:4].sum() - abs(capex.iloc[:4].sum())) / 1e9
        fcf_yield = (fcf_ttm / (f_info.market_cap / 1e9) * 100)

        fcf_str = f"({abs(fcf_ttm):,.1f})" if fcf_ttm < 0 else f"{fcf_ttm:,.1f}"
        fcf_yield_str = f"({abs(fcf_yield):.1f}%)" if fcf_yield < 0 else f"{fcf_yield:.1f}%"
        fcf_color = "#dc3545" if fcf_ttm < 0 else "#1a73e8"
        yield_color = "#dc3545" if fcf_yield < 0 else "#2e7d32"

        price_chart = create_price_chart(hist)

        return html.Div([
            html.Div([
                html.Div(f"{company_name} ({ticker_symbol})", className="stock-card-header"),
                html.Div([
                    dbc.Row([
                        dbc.Col([
                            html.H5("Price Performance", className="section-title"),
                            create_table(market_data, market_columns),
                            html.H5("Key Ratios", className="section-title"),
                            create_table(ratios_data, ratios_columns),
                            html.H5("Valuation Ratios", className="section-title"),
                            create_table(valuation_data, valuation_columns),
                            html.H5("Quarterly Financials", className="section-title"),
                            create_table(fin_data, fin_columns),
                            html.H5("Quarterly Cash Flow", className="section-title"),
                            create_table(cf_data, cf_columns),
                            html.H5("Free Cash Flow Summary", className="section-title"),
                            dbc.Row([
                                dbc.Col([
                                    html.Div([
                                        html.Div("Calculated TTM FCF", className="fcf-label"),
                                        html.Div(f"${fcf_str} Billion", className="fcf-value",
                                                style={"color": fcf_color})
                                    ], className="fcf-box")
                                ], width=6),
                                dbc.Col([
                                    html.Div([
                                        html.Div("Free Cash Flow Yield", className="fcf-label"),
                                        html.Div(fcf_yield_str, className="fcf-value",
                                                style={"color": yield_color})
                                    ], className="fcf-box success" if fcf_yield >= 0 else "fcf-box")
                                ], width=6),
                            ])
                        ], width=8),
                        dbc.Col([
                            html.Div([
                                html.Div([
                                    html.Div("Price Chart", className="info-section-title"),
                                    dcc.Graph(figure=price_chart, config={'displayModeBar': False})
                                ], className="info-section"),
                                html.Div([
                                    html.Div("Recent News", className="info-section-title"),
                                    get_news_section(ticker)
                                ], className="info-section"),
                                html.Div([
                                    html.Div("Upcoming Events", className="info-section-title"),
                                    get_earnings_section(ticker)
                                ], className="info-section"),
                                html.Div([
                                    html.Div("Analyst Estimates", className="info-section-title"),
                                    get_analyst_section(ticker)
                                ], className="info-section"),
                            ], className="info-panel")
                        ], width=4),
                    ])
                ], className="stock-card-body")
            ], className="stock-card")
        ])

    except Exception as e:
        return dbc.Alert(f"Error processing {ticker_symbol}: {e}", color="danger", className="mb-3")

# ============================================================================
# APP LAYOUT
# ============================================================================

def create_header(show_back=False):
    """Create header with optional back button"""
    nav_links = html.Div([
        html.A("Home", href="/"),
        html.A("Portfolio", href="/portfolio"),
        html.A("Trades", href="/portfolio/trades"),
        html.A("Analytics", href="/portfolio/analytics"),
        html.A("Finance", href="/finance"),
        html.A("Alerts", href="/alerts"),
        html.A("Search", href="/search"),
        html.A("Settings", href="/settings"),
    ], className="header-nav")

    return html.Div([
        html.Div([
            html.H1("Financial Dashboard", className="header-title"),
            nav_links
        ], className="header-content")
    ], className="main-header")

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    dcc.Store(id='url-ticker-store'),  # Store ticker from URL
    html.Div(id='header-container'),
    dbc.Container(id='page-content', fluid=True, style={"maxWidth": "1600px"})
])

# ============================================================================
# CALLBACKS
# ============================================================================

@app.callback(
    [Output('header-container', 'children'),
     Output('page-content', 'children'),
     Output('url-ticker-store', 'data')],
    [Input('url', 'pathname'),
     Input('url', 'search')]
)
def display_page(pathname, search):
    """Route to different pages based on URL"""
    header = create_header()
    ticker_from_url = None

    # Parse query string for ticker
    if search:
        from urllib.parse import parse_qs
        params = parse_qs(search.lstrip('?'))
        ticker_from_url = params.get('ticker', [None])[0]

    if pathname == '/watchlist':
        return header, create_watchlist_page(), None
    elif pathname == '/search':
        return header, create_search_page(), ticker_from_url
    elif pathname == '/portfolio':
        return header, create_portfolio_page(), None
    elif pathname == '/portfolio/trades':
        return header, create_trades_page(), None
    elif pathname == '/portfolio/analytics':
        return header, create_analytics_page(), None
    elif pathname == '/finance':
        return header, create_finance_hub_page(), None
    elif pathname == '/finance/income':
        return header, create_income_page(), None
    elif pathname == '/finance/expenses':
        return header, create_expenses_page(), None
    elif pathname == '/alerts':
        return header, create_alerts_page(), None
    elif pathname == '/settings':
        return header, create_settings_page(), None
    else:
        return header, create_landing_page(), None

@app.callback(
    Output('watchlist-preview-container', 'children'),
    Input('url', 'pathname')
)
def update_watchlist_preview(pathname):
    """Update watchlist preview on landing page"""
    if pathname == '/' or pathname is None:
        return create_watchlist_preview()
    return html.Div()

@app.callback(
    [Output('portfolio-summary-container', 'children'),
     Output('portfolio-filter-account', 'options')],
    [Input('url', 'pathname'),
     Input('portfolio-filter-account', 'value'),
     Input('portfolio-filter-ticker', 'value'),
     Input('portfolio-filter-date', 'value')]
)
def update_portfolio_summary(pathname, filter_account, filter_ticker, filter_date):
    """Update portfolio summary on landing page with filters"""
    portfolio = load_portfolio()
    accounts = portfolio.get("accounts", [])

    # Build account options for dropdown
    account_options = [{"label": "All Accounts", "value": "ALL"}] + \
                      [{"label": acc["name"], "value": acc["id"]} for acc in accounts]

    if pathname == '/' or pathname is None:
        return create_portfolio_summary(filter_account, filter_ticker, filter_date), account_options
    return html.Div(), account_options

@app.callback(
    Output('portfolio-trend-graph', 'figure'),
    [Input('time-1d', 'n_clicks'),
     Input('time-1w', 'n_clicks'),
     Input('time-1m', 'n_clicks'),
     Input('time-3m', 'n_clicks'),
     Input('time-6m', 'n_clicks'),
     Input('time-1y', 'n_clicks'),
     Input('time-all', 'n_clicks')],
    prevent_initial_call=True
)
def update_portfolio_graph(n1d, n1w, n1m, n3m, n6m, n1y, nall):
    """Update portfolio graph based on time filter"""
    ctx = callback_context
    if not ctx.triggered:
        return create_portfolio_trend_graph("1M")

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    time_map = {
        'time-1d': '1D',
        'time-1w': '1W',
        'time-1m': '1M',
        'time-3m': '3M',
        'time-6m': '6M',
        'time-1y': '1Y',
        'time-all': 'All'
    }
    time_filter = time_map.get(button_id, '1M')
    return create_portfolio_trend_graph(time_filter)

@app.callback(
    Output("results-container", "children"),
    [Input("run-button", "n_clicks"),
     Input("url-ticker-store", "data")],
    State("ticker-input", "value"),
    prevent_initial_call=True
)
def run_analysis(n_clicks, url_ticker, ticker_input):
    """Run stock analysis (original functionality)"""
    ctx = callback_context
    trigger = ctx.triggered[0]['prop_id'] if ctx.triggered else ''

    # Determine which ticker to use
    if 'url-ticker-store' in trigger and url_ticker:
        ticker_to_search = url_ticker
    else:
        ticker_to_search = ticker_input

    if not ticker_to_search or ticker_to_search.strip() == "":
        return dbc.Alert("Please enter at least one ticker symbol to search.", color="warning",
                        style={"borderRadius": "10px", "border": "none", "backgroundColor": "#fff3cd"})

    ticker_list = ticker_to_search.upper().replace(',', ' ').split()
    results = [analyze_ticker(ticker) for ticker in ticker_list]
    return results

@app.callback(
    Output("ticker-input", "value"),
    Input("url-ticker-store", "data"),
    prevent_initial_call=True
)
def fill_ticker_from_url(url_ticker):
    """Auto-fill ticker input from URL"""
    if url_ticker:
        return url_ticker.upper()
    return ""

@app.callback(
    Output('watchlist-full-container', 'children'),
    [Input('watchlist-add-btn', 'n_clicks'),
     Input({'type': 'watchlist-remove', 'ticker': ALL}, 'n_clicks')],
    [State('watchlist-add-input', 'value')],
    prevent_initial_call=True
)
def manage_watchlist(add_clicks, remove_clicks, new_ticker):
    """Add/remove stocks from watchlist"""
    ctx = callback_context
    if not ctx.triggered:
        return create_full_watchlist_view()

    trigger_id = ctx.triggered[0]['prop_id']
    watchlist = load_watchlist()

    if 'watchlist-add-btn' in trigger_id and new_ticker:
        ticker = new_ticker.upper().strip()
        if ticker and ticker not in watchlist['tickers']:
            # Validate ticker exists
            try:
                test = yf.Ticker(ticker)
                if test.fast_info.last_price:
                    watchlist['tickers'].insert(0, ticker)  # Add to top
                    save_watchlist(watchlist)
            except:
                pass
    elif 'watchlist-remove' in trigger_id:
        # Extract ticker from the trigger ID
        import ast
        trigger_dict = ast.literal_eval(trigger_id.split('.')[0])
        ticker_to_remove = trigger_dict['ticker']
        if ticker_to_remove in watchlist['tickers']:
            watchlist['tickers'].remove(ticker_to_remove)
            save_watchlist(watchlist)

    return create_full_watchlist_view()

def create_full_watchlist_view():
    """Create detailed watchlist view for watchlist page"""
    watchlist = load_watchlist()
    tickers = watchlist.get("tickers", [])

    if not tickers:
        return html.Div([
            html.Div("Your watchlist is empty", className="empty-state"),
            html.P("Add stocks using the input above", style={"color": "#888", "textAlign": "center"})
        ])

    rows = []
    for ticker in tickers:
        data = get_stock_quick_data(ticker)
        if data:
            change_1d, class_1d = format_change(data['change_1d'])
            change_1w, class_1w = format_change(data['change_1w'])
            change_1m, class_1m = format_change(data['change_1m'])

            rows.append(html.Tr([
                html.Td(ticker, style={"fontWeight": "600", "color": "#1a73e8"}),
                html.Td(f"${data['price']:.2f}"),
                html.Td(change_1d, className=class_1d),
                html.Td(change_1w, className=class_1w),
                html.Td(change_1m, className=class_1m),
                html.Td(
                    dbc.Button("Remove", id={'type': 'watchlist-remove', 'ticker': ticker},
                              className="remove-btn", size="sm")
                )
            ]))

    return html.Table([
        html.Thead(html.Tr([
            html.Th("Ticker"),
            html.Th("Price"),
            html.Th("1 Day"),
            html.Th("1 Week"),
            html.Th("1 Month"),
            html.Th("Action")
        ])),
        html.Tbody(rows)
    ], style={"width": "100%", "borderCollapse": "collapse"}, className="table table-hover")

@app.callback(
    Output('portfolio-accounts-container', 'children'),
    [Input('account-add-btn', 'n_clicks'),
     Input({'type': 'account-delete', 'id': ALL}, 'n_clicks'),
     Input({'type': 'holding-add-btn', 'account_id': ALL}, 'n_clicks'),
     Input({'type': 'holding-remove', 'account_id': ALL, 'ticker': ALL}, 'n_clicks')],
    [State('account-add-input', 'value'),
     State({'type': 'holding-ticker', 'account_id': ALL}, 'value'),
     State({'type': 'holding-shares', 'account_id': ALL}, 'value'),
     State({'type': 'holding-cost', 'account_id': ALL}, 'value')],
    prevent_initial_call=True
)
def manage_portfolio(add_account_clicks, delete_clicks, add_holding_clicks, remove_holding_clicks,
                     new_account_name, holding_tickers, holding_shares, holding_costs):
    """Manage portfolio accounts and holdings"""
    ctx = callback_context
    if not ctx.triggered:
        return create_full_portfolio_view()

    trigger_id = ctx.triggered[0]['prop_id']
    portfolio = load_portfolio()

    if 'account-add-btn' in trigger_id and new_account_name:
        new_account = {
            "id": str(uuid.uuid4()),
            "name": new_account_name.strip(),
            "holdings": []
        }
        portfolio['accounts'].append(new_account)
        save_portfolio(portfolio)

    elif 'account-delete' in trigger_id:
        import ast
        trigger_dict = ast.literal_eval(trigger_id.split('.')[0])
        account_id = trigger_dict['id']
        portfolio['accounts'] = [a for a in portfolio['accounts'] if a['id'] != account_id]
        save_portfolio(portfolio)

    elif 'holding-add-btn' in trigger_id:
        import ast
        trigger_dict = ast.literal_eval(trigger_id.split('.')[0])
        account_id = trigger_dict['account_id']

        # Find the index of this account's inputs
        for i, acc in enumerate(portfolio['accounts']):
            if acc['id'] == account_id:
                if i < len(holding_tickers) and holding_tickers[i] and holding_shares[i] and holding_costs[i]:
                    ticker = holding_tickers[i].upper().strip()
                    try:
                        test = yf.Ticker(ticker)
                        if test.fast_info.last_price:
                            acc['holdings'].append({
                                "ticker": ticker,
                                "shares": float(holding_shares[i]),
                                "avg_cost": float(holding_costs[i])
                            })
                            save_portfolio(portfolio)
                    except:
                        pass
                break

    elif 'holding-remove' in trigger_id:
        import ast
        trigger_dict = ast.literal_eval(trigger_id.split('.')[0])
        account_id = trigger_dict['account_id']
        ticker_to_remove = trigger_dict['ticker']

        for acc in portfolio['accounts']:
            if acc['id'] == account_id:
                acc['holdings'] = [h for h in acc['holdings'] if h['ticker'] != ticker_to_remove]
                save_portfolio(portfolio)
                break

    return create_full_portfolio_view()

def create_full_portfolio_view():
    """Create detailed portfolio view"""
    portfolio = load_portfolio()
    accounts = portfolio.get("accounts", [])

    if not accounts:
        return html.Div([
            html.Div("No portfolio accounts", className="empty-state"),
            html.P("Create an account using the input above", style={"color": "#888", "textAlign": "center"})
        ])

    account_cards = []
    grand_total_value = 0
    grand_total_cost = 0

    for acc in accounts:
        holdings_rows = []
        account_total_value = 0
        account_total_cost = 0

        for holding in acc.get("holdings", []):
            data = get_stock_quick_data(holding["ticker"])
            if data:
                current_val = data["price"] * holding["shares"]
                cost_basis = holding["avg_cost"] * holding["shares"]
                gain_loss = current_val - cost_basis
                gain_pct = (gain_loss / cost_basis) * 100 if cost_basis > 0 else 0

                account_total_value += current_val
                account_total_cost += cost_basis

                gain_class = "positive" if gain_loss >= 0 else "negative"
                gain_str = f"+${gain_loss:,.2f}" if gain_loss >= 0 else f"-${abs(gain_loss):,.2f}"
                pct_str = f"+{gain_pct:.1f}%" if gain_pct >= 0 else f"{gain_pct:.1f}%"

                holdings_rows.append(html.Tr([
                    html.Td(holding["ticker"], style={"fontWeight": "600", "color": "#1a73e8"}),
                    html.Td(f"{holding['shares']:.2f}"),
                    html.Td(f"${holding['avg_cost']:.2f}"),
                    html.Td(f"${data['price']:.2f}"),
                    html.Td(f"${current_val:,.2f}"),
                    html.Td(html.Span(f"{gain_str} ({pct_str})", className=gain_class)),
                    html.Td(
                        dbc.Button("X", id={'type': 'holding-remove', 'account_id': acc['id'],
                                           'ticker': holding['ticker']},
                                  className="remove-btn", size="sm")
                    )
                ]))

        grand_total_value += account_total_value
        grand_total_cost += account_total_cost

        account_gain = account_total_value - account_total_cost
        account_gain_class = "positive" if account_gain >= 0 else "negative"
        account_gain_str = f"+${account_gain:,.2f}" if account_gain >= 0 else f"-${abs(account_gain):,.2f}"

        holdings_table = html.Table([
            html.Thead(html.Tr([
                html.Th("Ticker"),
                html.Th("Shares"),
                html.Th("Avg Cost"),
                html.Th("Current"),
                html.Th("Value"),
                html.Th("Gain/Loss"),
                html.Th("")
            ])),
            html.Tbody(holdings_rows)
        ], style={"width": "100%"}, className="table table-hover") if holdings_rows else html.P("No holdings", style={"color": "#888"})

        account_cards.append(html.Div([
            html.Div([
                html.Div([
                    html.Span(acc['name'], style={"fontSize": "1.2rem", "fontWeight": "600"}),
                    html.Span(f" | Total: ${account_total_value:,.2f} ", style={"marginLeft": "15px"}),
                    html.Span(account_gain_str, className=account_gain_class, style={"fontWeight": "600"}),
                ], style={"flex": "1"}),
                dbc.Button("Delete Account", id={'type': 'account-delete', 'id': acc['id']},
                          color="danger", size="sm", outline=True)
            ], style={"display": "flex", "justifyContent": "space-between", "alignItems": "center",
                     "marginBottom": "15px", "paddingBottom": "10px", "borderBottom": "2px solid #e3f2fd"}),

            holdings_table,

            # Add holding form
            html.Div([
                dbc.Row([
                    dbc.Col(dbc.Input(id={'type': 'holding-ticker', 'account_id': acc['id']},
                                     placeholder="Ticker", className="add-input"), width=3),
                    dbc.Col(dbc.Input(id={'type': 'holding-shares', 'account_id': acc['id']},
                                     placeholder="Shares", type="number", className="add-input"), width=3),
                    dbc.Col(dbc.Input(id={'type': 'holding-cost', 'account_id': acc['id']},
                                     placeholder="Avg Cost", type="number", className="add-input"), width=3),
                    dbc.Col(dbc.Button("Add", id={'type': 'holding-add-btn', 'account_id': acc['id']},
                                      className="add-btn", style={"width": "100%"}), width=3),
                ])
            ], style={"marginTop": "15px", "paddingTop": "15px", "borderTop": "1px solid #e3f2fd"})
        ], className="stock-card", style={"padding": "20px", "marginBottom": "20px"}))

    # Grand total
    grand_gain = grand_total_value - grand_total_cost
    grand_gain_class = "positive" if grand_gain >= 0 else "negative"
    grand_gain_str = f"+${grand_gain:,.2f}" if grand_gain >= 0 else f"-${abs(grand_gain):,.2f}"

    account_cards.append(html.Div([
        html.H5("Portfolio Total", style={"marginBottom": "10px"}),
        html.Div([
            html.Span(f"${grand_total_value:,.2f}", style={"fontSize": "1.5rem", "fontWeight": "600", "marginRight": "20px"}),
            html.Span(grand_gain_str, className=grand_gain_class, style={"fontSize": "1.3rem", "fontWeight": "600"})
        ])
    ], className="total-row"))

    return html.Div(account_cards)

# ============================================================================
# TRADES CSV IMPORT CALLBACKS (Split into two for proper functionality)
# ============================================================================

# Helper functions for CSV import
def _get_yf_ticker_for_import(ticker):
    """Convert ticker to Yahoo Finance format"""
    CRYPTO_MAP = {'BTC': 'BTC-USD', 'ETH': 'ETH-USD', 'SOL': 'SOL-USD',
                  'XRP': 'XRP-USD', 'DOGE': 'DOGE-USD'}
    return CRYPTO_MAP.get(ticker.upper().strip(), ticker.upper().strip())

def _get_current_price_for_import(ticker):
    """Get current price for a ticker"""
    yf_ticker = _get_yf_ticker_for_import(ticker)
    try:
        stock = yf.Ticker(yf_ticker)
        hist = stock.history(period="1d")
        if not hist.empty:
            return float(hist['Close'].iloc[-1])
        info = stock.info
        return info.get('regularMarketPrice') or info.get('currentPrice') or 0
    except:
        return 0

# Callback 1: Handle CSV upload - show preview
@app.callback(
    [Output('trades-csv-preview', 'children'),
     Output('trades-csv-data-store', 'data')],
    [Input('trades-csv-upload', 'contents')],
    [State('trades-csv-upload', 'filename')],
    prevent_initial_call=True
)
def handle_trades_csv_upload(contents, filename):
    """Handle CSV upload and show preview"""
    if not contents:
        return html.Div(), None

    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string).decode('utf-8')
        lines = decoded.strip().split('\n')

        # Parse CSV
        reader = csv.DictReader(lines)
        rows = list(reader)

        if not rows:
            return html.Div("No data found in CSV", style={"color": "red"}), None

        # Group by account for preview
        accounts_preview = {}
        for row in rows:
            account = row.get('Investment Account', '').strip()
            ticker = row.get('Ticker', '').strip()
            shares = row.get('Amount of Stock', '0')
            stock_type = row.get('Type', '').strip()

            if account not in accounts_preview:
                accounts_preview[account] = []
            accounts_preview[account].append({
                'ticker': ticker,
                'shares': shares,
                'type': stock_type
            })

        # Create preview table
        preview_rows = []
        for acc, holdings in accounts_preview.items():
            for h in holdings:
                preview_rows.append(html.Tr([
                    html.Td(acc, style={"fontSize": "0.85rem"}),
                    html.Td(h['type'], style={"fontSize": "0.85rem"}),
                    html.Td(h['ticker'], style={"fontWeight": "600", "color": "#1a73e8"}),
                    html.Td(h['shares'], style={"fontSize": "0.85rem"})
                ]))

        preview = html.Div([
            html.H5(f"Preview: {filename}", style={"marginBottom": "10px"}),
            html.P(f"Found {len(accounts_preview)} accounts with {len(rows)} holdings total",
                  style={"color": "#666", "fontSize": "0.85rem"}),
            html.Table([
                html.Thead(html.Tr([
                    html.Th("Account"), html.Th("Type"), html.Th("Ticker"), html.Th("Shares")
                ], style={"fontSize": "0.85rem", "color": "#666"})),
                html.Tbody(preview_rows[:15])  # Show first 15 rows
            ], className="table", style={"fontSize": "0.9rem", "marginBottom": "15px"}),
            html.P(f"Showing first 15 of {len(rows)} rows..." if len(rows) > 15 else "",
                  style={"color": "#888", "fontSize": "0.8rem"}),
            dbc.Button(f"Import {len(rows)} Holdings (Fetches Current Prices)",
                      id={'type': 'trades-csv-import-btn', 'index': 0}, color="success",
                      style={"marginTop": "10px"})
        ])

        return preview, {'contents': contents, 'filename': filename}

    except Exception as e:
        return html.Div(f"Error parsing CSV: {str(e)}", style={"color": "red"}), None

# Callback 2: Handle import button click (using pattern-matching callback)
@app.callback(
    Output('trades-csv-preview', 'children', allow_duplicate=True),
    [Input({'type': 'trades-csv-import-btn', 'index': ALL}, 'n_clicks')],
    [State('trades-csv-data-store', 'data')],
    prevent_initial_call=True
)
def handle_trades_csv_import(n_clicks_list, stored_data):
    """Handle import button click to process CSV data"""
    # Check if any button was actually clicked
    if not n_clicks_list or not any(n_clicks_list) or not stored_data:
        raise PreventUpdate

    try:
        contents = stored_data.get('contents')
        filename = stored_data.get('filename')

        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string).decode('utf-8')
        lines = decoded.strip().split('\n')
        reader = csv.DictReader(lines)
        rows = list(reader)

        # Load current data
        portfolio = load_portfolio()
        trades_data = load_trades()
        today = datetime.now().strftime("%Y-%m-%d")

        # Track new accounts created
        account_map = {acc['name']: acc['id'] for acc in portfolio.get('accounts', [])}
        new_accounts = 0
        new_holdings = 0
        prices_fetched = {}

        # Process each row
        for row in rows:
            account_name = row.get('Investment Account', '').strip()
            ticker = row.get('Ticker', '').strip()
            shares = float(row.get('Amount of Stock', 0))

            if not account_name or not ticker or shares <= 0:
                continue

            # Create account if doesn't exist
            if account_name not in account_map:
                new_id = str(uuid.uuid4())
                portfolio['accounts'].append({
                    'id': new_id,
                    'name': account_name,
                    'holdings': []
                })
                account_map[account_name] = new_id
                new_accounts += 1

            account_id = account_map[account_name]
            yf_ticker = _get_yf_ticker_for_import(ticker)

            # Get price (cache for efficiency)
            if yf_ticker not in prices_fetched:
                prices_fetched[yf_ticker] = _get_current_price_for_import(ticker)
            price = prices_fetched[yf_ticker]

            if price <= 0:
                continue

            # Find account and add/update holding
            for acc in portfolio['accounts']:
                if acc['id'] == account_id:
                    # Check if holding exists
                    holding_found = False
                    for h in acc['holdings']:
                        if h['ticker'] == yf_ticker:
                            # Update existing - average cost
                            old_total = h['shares'] * h['avg_cost']
                            new_total = shares * price
                            h['shares'] += shares
                            h['avg_cost'] = (old_total + new_total) / h['shares']
                            holding_found = True
                            break

                    if not holding_found:
                        acc['holdings'].append({
                            'ticker': yf_ticker,
                            'shares': shares,
                            'avg_cost': price
                        })
                        new_holdings += 1

                    # Add trade entry
                    trades_data['trades'].append({
                        'id': str(uuid.uuid4()),
                        'date': today,
                        'account_id': account_id,
                        'ticker': yf_ticker,
                        'action': 'BUY',
                        'shares': shares,
                        'price': price,
                        'fees': 0.0,
                        'notes': f'Imported from {filename}'
                    })
                    break

        # Save data
        save_portfolio(portfolio)
        save_trades(trades_data)

        return html.Div([
            html.Div([
                html.I(className="fas fa-check-circle", style={"color": "#28a745", "fontSize": "2rem", "marginRight": "10px"}),
                html.Span("Import Complete!", style={"fontSize": "1.2rem", "fontWeight": "600", "color": "#28a745"})
            ], style={"display": "flex", "alignItems": "center", "marginBottom": "15px"}),
            html.P(f"Created {new_accounts} new accounts" if new_accounts > 0 else "", style={"marginBottom": "5px"}),
            html.P(f"Added {new_holdings} new holdings", style={"marginBottom": "5px"}),
            html.P(f"Created {len(rows)} trade entries", style={"marginBottom": "5px"}),
            html.P("Refresh the page to see updated portfolio.", style={"color": "#666", "fontSize": "0.85rem"})
        ], style={"padding": "20px", "backgroundColor": "#d4edda", "borderRadius": "10px"})

    except Exception as e:
        return html.Div(f"Error importing: {str(e)}", style={"color": "red"})

# ============================================================================
# TRADE HISTORY CALLBACKS
# ============================================================================

@app.callback(
    [Output('trades-container', 'children'),
     Output('realized-gains-container', 'children')],
    [Input('trade-add-btn', 'n_clicks'),
     Input('trade-filter-account', 'value'),
     Input('trade-filter-action', 'value'),
     Input('trade-filter-ticker', 'value'),
     Input({'type': 'trade-delete', 'id': ALL}, 'n_clicks')],
    [State('trade-account', 'value'),
     State('trade-date', 'value'),
     State('trade-action', 'value'),
     State('trade-ticker', 'value'),
     State('trade-shares', 'value'),
     State('trade-price', 'value'),
     State('trade-fees', 'value'),
     State('trade-notes', 'value')],
    prevent_initial_call=False
)
def manage_trades(add_clicks, filter_account, filter_action, filter_ticker,
                  delete_clicks, account_id, trade_date, action, ticker,
                  shares, price, fees, notes):
    """Manage trade history"""
    ctx = callback_context
    trades_data = load_trades()
    portfolio = load_portfolio()

    # Handle add trade
    if ctx.triggered and 'trade-add-btn' in ctx.triggered[0]['prop_id']:
        if all([account_id, trade_date, action, ticker, shares, price]):
            ticker_clean = ticker.upper().strip()
            shares_float = float(shares)
            price_float = float(price)

            new_trade = {
                "id": str(uuid.uuid4()),
                "date": trade_date,
                "account_id": account_id,
                "ticker": ticker_clean,
                "action": action,
                "shares": shares_float,
                "price": price_float,
                "fees": float(fees) if fees else 0.0,
                "notes": notes or ""
            }
            trades_data['trades'].append(new_trade)
            save_trades(trades_data)

            # Sync trade to portfolio holdings
            for account in portfolio.get('accounts', []):
                if account['id'] == account_id:
                    # Find existing holding or create new one
                    holding_found = False
                    for holding in account.get('holdings', []):
                        if holding['ticker'] == ticker_clean:
                            holding_found = True
                            if action == 'BUY':
                                # Calculate new average cost
                                old_total = holding['shares'] * holding['avg_cost']
                                new_total = shares_float * price_float
                                new_shares = holding['shares'] + shares_float
                                if new_shares > 0:
                                    holding['avg_cost'] = (old_total + new_total) / new_shares
                                holding['shares'] = new_shares
                            else:  # SELL
                                holding['shares'] -= shares_float
                                # Remove holding if shares go to 0 or negative
                                if holding['shares'] <= 0:
                                    account['holdings'].remove(holding)
                            break

                    # If no existing holding and it's a BUY, create new holding
                    if not holding_found and action == 'BUY':
                        if 'holdings' not in account:
                            account['holdings'] = []
                        account['holdings'].append({
                            'ticker': ticker_clean,
                            'shares': shares_float,
                            'avg_cost': price_float
                        })
                    break

            save_portfolio(portfolio)

    # Handle delete trade
    if ctx.triggered and 'trade-delete' in ctx.triggered[0]['prop_id']:
        import ast
        trigger_dict = ast.literal_eval(ctx.triggered[0]['prop_id'].split('.')[0])
        trade_id = trigger_dict['id']

        # Find the trade to reverse portfolio changes
        trade_to_delete = next((t for t in trades_data['trades'] if t['id'] == trade_id), None)
        if trade_to_delete:
            # Reverse the portfolio changes
            for account in portfolio.get('accounts', []):
                if account['id'] == trade_to_delete['account_id']:
                    for holding in account.get('holdings', []):
                        if holding['ticker'] == trade_to_delete['ticker']:
                            if trade_to_delete['action'] == 'BUY':
                                # Reverse BUY: subtract shares
                                holding['shares'] -= trade_to_delete['shares']
                                if holding['shares'] <= 0:
                                    account['holdings'].remove(holding)
                            else:  # Reverse SELL: add shares back
                                holding['shares'] += trade_to_delete['shares']
                            break
                    break
            save_portfolio(portfolio)

        trades_data['trades'] = [t for t in trades_data['trades'] if t['id'] != trade_id]
        save_trades(trades_data)

    # Filter trades
    filtered_trades = trades_data.get('trades', [])
    if filter_account and filter_account != 'ALL':
        filtered_trades = [t for t in filtered_trades if t.get('account_id') == filter_account]
    if filter_action and filter_action != 'ALL':
        filtered_trades = [t for t in filtered_trades if t.get('action') == filter_action]
    if filter_ticker:
        filtered_trades = [t for t in filtered_trades if filter_ticker.upper() in t.get('ticker', '').upper()]

    # Sort by date descending
    filtered_trades = sorted(filtered_trades, key=lambda x: x.get('date', ''), reverse=True)

    # Get account names
    account_names = {acc['id']: acc['name'] for acc in portfolio.get('accounts', [])}

    # Build trades table
    if not filtered_trades:
        trades_table = html.P("No trades recorded yet.", style={"color": "#888"})
    else:
        rows = []
        for trade in filtered_trades:
            total_value = trade['shares'] * trade['price']
            rows.append(html.Tr([
                html.Td(trade['date']),
                html.Td(account_names.get(trade['account_id'], 'Unknown')),
                html.Td(trade['ticker'], style={"fontWeight": "600", "color": "#1a73e8"}),
                html.Td(trade['action'],
                       style={"color": "#2e7d32" if trade['action'] == 'BUY' else "#dc3545", "fontWeight": "600"}),
                html.Td(f"{trade['shares']:.2f}"),
                html.Td(f"${trade['price']:.2f}"),
                html.Td(f"${total_value:,.2f}"),
                html.Td(f"${trade.get('fees', 0):.2f}"),
                html.Td(trade.get('notes', '')[:30] + ('...' if len(trade.get('notes', '')) > 30 else '')),
                html.Td(dbc.Button("X", id={'type': 'trade-delete', 'id': trade['id']},
                                  className="remove-btn", size="sm"))
            ]))

        trades_table = html.Table([
            html.Thead(html.Tr([
                html.Th("Date"), html.Th("Account"), html.Th("Ticker"),
                html.Th("Action"), html.Th("Shares"), html.Th("Price"),
                html.Th("Total"), html.Th("Fees"), html.Th("Notes"), html.Th("")
            ])),
            html.Tbody(rows)
        ], className="table table-hover", style={"width": "100%"})

    # Calculate realized gains (FIFO)
    realized_gains = calculate_realized_gains(trades_data.get('trades', []))

    if not realized_gains:
        gains_display = html.P("No closed positions yet.", style={"color": "#888"})
    else:
        gains_rows = []
        total_realized = 0
        for ticker, data in realized_gains.items():
            gain_class = "positive" if data['gain'] >= 0 else "negative"
            gain_str = f"+${data['gain']:,.2f}" if data['gain'] >= 0 else f"-${abs(data['gain']):,.2f}"
            gains_rows.append(html.Tr([
                html.Td(ticker, style={"fontWeight": "600", "color": "#1a73e8"}),
                html.Td(f"{data['shares_sold']:.2f}"),
                html.Td(f"${data['cost_basis']:,.2f}"),
                html.Td(f"${data['proceeds']:,.2f}"),
                html.Td(html.Span(gain_str, className=gain_class), style={"fontWeight": "600"})
            ]))
            total_realized += data['gain']

        total_class = "positive" if total_realized >= 0 else "negative"
        total_str = f"+${total_realized:,.2f}" if total_realized >= 0 else f"-${abs(total_realized):,.2f}"

        gains_display = html.Div([
            html.Table([
                html.Thead(html.Tr([
                    html.Th("Ticker"), html.Th("Shares Sold"),
                    html.Th("Cost Basis"), html.Th("Proceeds"), html.Th("Realized Gain/Loss")
                ])),
                html.Tbody(gains_rows)
            ], className="table table-hover", style={"width": "100%"}),
            html.Div([
                html.Strong("Total Realized: "),
                html.Span(total_str, className=total_class, style={"fontSize": "1.2rem", "fontWeight": "700"})
            ], style={"marginTop": "15px", "padding": "15px", "backgroundColor": "#f8fbff", "borderRadius": "10px"})
        ])

    return trades_table, gains_display

def calculate_realized_gains(trades):
    """Calculate realized gains using FIFO method"""
    # Group trades by ticker
    by_ticker = {}
    for trade in sorted(trades, key=lambda x: x.get('date', '')):
        ticker = trade.get('ticker', '')
        if ticker not in by_ticker:
            by_ticker[ticker] = {'buys': [], 'sells': []}
        if trade['action'] == 'BUY':
            by_ticker[ticker]['buys'].append({
                'shares': trade['shares'],
                'price': trade['price'],
                'remaining': trade['shares']
            })
        else:
            by_ticker[ticker]['sells'].append({
                'shares': trade['shares'],
                'price': trade['price']
            })

    # Calculate realized gains
    realized = {}
    for ticker, data in by_ticker.items():
        if not data['sells']:
            continue

        total_cost = 0
        total_proceeds = 0
        total_shares_sold = 0

        for sell in data['sells']:
            shares_to_sell = sell['shares']
            proceeds = sell['shares'] * sell['price']
            total_proceeds += proceeds
            total_shares_sold += sell['shares']

            # FIFO: use oldest buys first
            for buy in data['buys']:
                if shares_to_sell <= 0:
                    break
                if buy['remaining'] <= 0:
                    continue

                used = min(buy['remaining'], shares_to_sell)
                total_cost += used * buy['price']
                buy['remaining'] -= used
                shares_to_sell -= used

        if total_shares_sold > 0:
            realized[ticker] = {
                'shares_sold': total_shares_sold,
                'cost_basis': total_cost,
                'proceeds': total_proceeds,
                'gain': total_proceeds - total_cost
            }

    return realized

# ============================================================================
# INCOME TRACKING CALLBACKS (Redesigned)
# ============================================================================

# Income type colors
INCOME_TYPE_COLORS = {
    "SALARY": "#2e7d32",
    "DIVIDEND": "#1a73e8",
    "INTEREST": "#f57c00",
    "BONUS": "#9c27b0",
    "RSU": "#00bcd4",
    "OTHER": "#607d8b"
}

INCOME_TYPE_LABELS = {
    "SALARY": "Salary",
    "DIVIDEND": "Dividend",
    "INTEREST": "Interest",
    "BONUS": "Bonus",
    "RSU": "RSU",
    "OTHER": "Other"
}

# Callback: Tab switching for income input
@app.callback(
    [Output('income-onetime-form', 'style'),
     Output('income-recurring-form', 'style'),
     Output('income-rsu-form', 'style')],
    Input('income-input-tabs', 'active_tab'),
    prevent_initial_call=False
)
def toggle_income_input_tabs(active_tab):
    if active_tab == 'tab-add-income':
        return {"display": "block"}, {"display": "none"}, {"display": "none"}
    elif active_tab == 'tab-recurring':
        return {"display": "none"}, {"display": "block"}, {"display": "none"}
    else:
        return {"display": "none"}, {"display": "none"}, {"display": "block"}

# Callback: Month navigation and overview
@app.callback(
    [Output('income-selected-month', 'data'),
     Output('income-month-display', 'children'),
     Output('income-this-month-total', 'children'),
     Output('income-ytd-total', 'children'),
     Output('income-rsu-value', 'children'),
     Output('income-vs-last-month', 'children'),
     Output('income-vs-last-month', 'style')],
    [Input('income-month-prev', 'n_clicks'),
     Input('income-month-next', 'n_clicks'),
     Input('income-refresh-trigger', 'data')],
    State('income-selected-month', 'data'),
    prevent_initial_call=False
)
def update_income_overview(prev_clicks, next_clicks, refresh, current_month):
    ctx = callback_context
    income_data = load_income()
    incomes = income_data.get('income', [])
    rsus = income_data.get('rsus', [])

    if current_month is None:
        current_month = datetime.now().strftime("%Y-%m")

    # Handle month navigation
    if ctx.triggered:
        trigger = ctx.triggered[0]['prop_id']
        if 'income-month-prev' in trigger:
            dt = datetime.strptime(current_month, "%Y-%m")
            dt = dt - relativedelta(months=1)
            current_month = dt.strftime("%Y-%m")
        elif 'income-month-next' in trigger:
            dt = datetime.strptime(current_month, "%Y-%m")
            dt = dt + relativedelta(months=1)
            current_month = dt.strftime("%Y-%m")

    # Format month display
    try:
        month_dt = datetime.strptime(current_month, "%Y-%m")
        month_display = month_dt.strftime("%B %Y")
    except:
        month_display = current_month

    # Calculate totals
    month_income = sum(i.get('amount', 0) for i in incomes if i.get('date', '').startswith(current_month))

    current_year = current_month[:4]
    ytd_income = sum(i.get('amount', 0) for i in incomes if i.get('date', '').startswith(current_year))

    # Calculate RSU value
    rsu_total = 0
    for rsu in rsus:
        current_price = rsu.get('current_price', rsu.get('grant_price', 0))
        shares = rsu.get('shares', 0)
        rsu_total += current_price * shares

    # vs Last Month
    try:
        prev_month_dt = datetime.strptime(current_month, "%Y-%m") - relativedelta(months=1)
        prev_month = prev_month_dt.strftime("%Y-%m")
    except:
        prev_month = current_month

    prev_income = sum(i.get('amount', 0) for i in incomes if i.get('date', '').startswith(prev_month))

    if prev_income > 0:
        change_pct = ((month_income - prev_income) / prev_income) * 100
        if change_pct > 0:
            vs_last = f"+{change_pct:.0f}%"
            vs_last_style = {"margin": "0", "fontWeight": "700", "color": "#2e7d32"}
        else:
            vs_last = f"{change_pct:.0f}%"
            vs_last_style = {"margin": "0", "fontWeight": "700", "color": "#dc3545"}
    else:
        vs_last = "N/A"
        vs_last_style = {"margin": "0", "fontWeight": "700", "color": "#888"}

    return (current_month, month_display, f"${month_income:,.2f}", f"${ytd_income:,.2f}",
            f"${rsu_total:,.2f}", vs_last, vs_last_style)

# Callback: Charts
@app.callback(
    [Output('income-pie-chart', 'figure'),
     Output('income-trend-chart', 'figure')],
    [Input('income-selected-month', 'data'),
     Input('income-refresh-trigger', 'data')],
    prevent_initial_call=False
)
def update_income_charts(selected_month, refresh):
    income_data = load_income()
    incomes = income_data.get('income', [])

    if selected_month is None:
        selected_month = datetime.now().strftime("%Y-%m")

    # Pie chart by type (for selected month)
    month_incomes = [i for i in incomes if i.get('date', '').startswith(selected_month)]
    type_totals = {}
    for i in month_incomes:
        t = i.get('type', 'OTHER')
        type_totals[t] = type_totals.get(t, 0) + i.get('amount', 0)

    if type_totals:
        labels = [INCOME_TYPE_LABELS.get(t, t) for t in type_totals.keys()]
        colors = [INCOME_TYPE_COLORS.get(t, "#888") for t in type_totals.keys()]
        pie_fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=list(type_totals.values()),
            hole=0.45,
            marker_colors=colors,
            textinfo='label+percent',
            textposition='outside'
        )])
        pie_fig.update_layout(
            margin=dict(l=20, r=20, t=30, b=20),
            height=260,
            showlegend=False,
            font=dict(size=11)
        )
    else:
        pie_fig = go.Figure()
        pie_fig.add_annotation(text="No income this month", x=0.5, y=0.5, showarrow=False,
                              font=dict(size=14, color="#888"))
        pie_fig.update_layout(height=260, margin=dict(l=20, r=20, t=30, b=20))

    # Monthly trend (last 6 months)
    monthly_data = {}
    for i in incomes:
        month = i.get('date', '')[:7]
        if month:
            monthly_data[month] = monthly_data.get(month, 0) + i.get('amount', 0)

    if monthly_data:
        sorted_months = sorted(monthly_data.keys())[-6:]
        month_labels = [datetime.strptime(m, "%Y-%m").strftime("%b '%y") for m in sorted_months]
        colors = ['#2e7d32' if m != selected_month else '#1a73e8' for m in sorted_months]

        max_val = max(monthly_data[m] for m in sorted_months)
        y_max = max_val * 1.15

        trend_fig = go.Figure(data=[go.Bar(
            x=month_labels,
            y=[monthly_data[m] for m in sorted_months],
            marker_color=colors,
            text=[f"${monthly_data[m]:,.0f}" for m in sorted_months],
            textposition='outside',
            customdata=sorted_months,
            hovertemplate='%{x}<br>$%{y:,.2f}<extra></extra>'
        )])
        trend_fig.update_layout(
            margin=dict(l=50, r=20, t=30, b=40),
            height=260,
            yaxis=dict(tickprefix='$', tickformat=',', range=[0, y_max]),
            showlegend=False,
            font=dict(size=11),
            bargap=0.3
        )
    else:
        trend_fig = go.Figure()
        trend_fig.add_annotation(text="No income data", x=0.5, y=0.5, showarrow=False,
                                font=dict(size=14, color="#888"))
        trend_fig.update_layout(height=260, margin=dict(l=20, r=20, t=30, b=20))

    return pie_fig, trend_fig

# Callback: Click on trend chart to filter
@app.callback(
    [Output('income-selected-month', 'data', allow_duplicate=True),
     Output('income-filter-month', 'value')],
    Input('income-trend-chart', 'clickData'),
    prevent_initial_call=True
)
def handle_income_chart_click(click_data):
    if click_data and 'points' in click_data:
        point = click_data['points'][0]
        if 'customdata' in point:
            clicked_month = point['customdata']
            return clicked_month, clicked_month
    raise PreventUpdate

# Callback: Add one-time income
@app.callback(
    Output('income-refresh-trigger', 'data', allow_duplicate=True),
    Input('income-add-btn', 'n_clicks'),
    [State('income-date', 'value'),
     State('income-type', 'value'),
     State('income-source', 'value'),
     State('income-amount', 'value')],
    prevent_initial_call=True
)
def add_income(n_clicks, income_date, income_type, source, amount):
    if not all([income_date, income_type, source, amount]):
        raise PreventUpdate

    income_data = load_income()
    new_income = {
        "id": str(uuid.uuid4()),
        "date": income_date,
        "type": income_type,
        "source": source,
        "amount": float(amount)
    }
    income_data['income'].append(new_income)
    save_income(income_data)

    return str(datetime.now())

# Callback: Add recurring income
@app.callback(
    Output('income-refresh-trigger', 'data', allow_duplicate=True),
    Input('recurring-add-btn', 'n_clicks'),
    [State('recurring-desc', 'value'),
     State('recurring-amount', 'value'),
     State('recurring-weeks', 'value'),
     State('recurring-start', 'value')],
    prevent_initial_call=True
)
def add_recurring_income(n_clicks, desc, amount, weeks, start_date):
    if not all([desc, amount, weeks, start_date]):
        raise PreventUpdate

    income_data = load_income()
    new_recurring = {
        "id": str(uuid.uuid4()),
        "description": desc,
        "amount": float(amount),
        "weeks_interval": weeks,
        "start_date": start_date,
        "active": True
    }
    income_data['recurring'].append(new_recurring)
    save_income(income_data)

    return str(datetime.now())

# Callback: Display recurring income list
@app.callback(
    Output('recurring-income-list', 'children'),
    [Input('income-refresh-trigger', 'data'),
     Input({'type': 'recurring-delete', 'id': ALL}, 'n_clicks'),
     Input({'type': 'recurring-generate', 'id': ALL}, 'n_clicks')],
    prevent_initial_call=False
)
def display_recurring_income(refresh, delete_clicks, generate_clicks):
    ctx = callback_context
    income_data = load_income()

    # Handle delete
    if ctx.triggered and 'recurring-delete' in ctx.triggered[0]['prop_id']:
        import ast
        trigger_dict = ast.literal_eval(ctx.triggered[0]['prop_id'].split('.')[0])
        rec_id = trigger_dict['id']
        income_data['recurring'] = [r for r in income_data['recurring'] if r['id'] != rec_id]
        save_income(income_data)

    # Handle generate (add income entries up to today)
    if ctx.triggered and 'recurring-generate' in ctx.triggered[0]['prop_id']:
        import ast
        trigger_dict = ast.literal_eval(ctx.triggered[0]['prop_id'].split('.')[0])
        rec_id = trigger_dict['id']

        for rec in income_data['recurring']:
            if rec['id'] == rec_id:
                start = datetime.strptime(rec['start_date'], "%Y-%m-%d")
                weeks = rec['weeks_interval']
                today = datetime.now()

                # Find existing income dates for this recurring source
                existing_dates = set(i.get('date') for i in income_data['income']
                                    if i.get('source') == rec['description'])

                # Generate entries
                current_date = start
                while current_date <= today:
                    date_str = current_date.strftime("%Y-%m-%d")
                    if date_str not in existing_dates:
                        income_data['income'].append({
                            "id": str(uuid.uuid4()),
                            "date": date_str,
                            "type": "SALARY",
                            "source": rec['description'],
                            "amount": rec['amount']
                        })
                    current_date += timedelta(weeks=weeks)
                break
        save_income(income_data)

    recurring = income_data.get('recurring', [])

    if not recurring:
        return html.P("No recurring income set up.", style={"color": "#888"})

    rows = []
    for rec in recurring:
        interval_text = f"Every {rec['weeks_interval']} week(s)"
        rows.append(html.Tr([
            html.Td(rec['description'], style={"fontWeight": "600"}),
            html.Td(f"${rec['amount']:,.2f}", style={"color": "#2e7d32"}),
            html.Td(interval_text),
            html.Td(rec['start_date']),
            html.Td([
                dbc.Button("Generate", id={'type': 'recurring-generate', 'id': rec['id']},
                          color="success", size="sm", style={"marginRight": "5px"}),
                dbc.Button("Delete", id={'type': 'recurring-delete', 'id': rec['id']},
                          color="danger", size="sm", outline=True)
            ])
        ]))

    return html.Table([
        html.Thead(html.Tr([html.Th("Description"), html.Th("Amount"), html.Th("Frequency"),
                           html.Th("Start Date"), html.Th("Actions")])),
        html.Tbody(rows)
    ], className="table", style={"width": "100%"})

# Callback: Add RSU
@app.callback(
    Output('income-refresh-trigger', 'data', allow_duplicate=True),
    Input('rsu-add-btn', 'n_clicks'),
    [State('rsu-ticker', 'value'),
     State('rsu-shares', 'value'),
     State('rsu-vest-date', 'value'),
     State('rsu-grant-price', 'value')],
    prevent_initial_call=True
)
def add_rsu(n_clicks, ticker, shares, vest_date, grant_price):
    if not all([ticker, shares, vest_date, grant_price]):
        raise PreventUpdate

    income_data = load_income()

    # Get current price
    try:
        stock = yf.Ticker(ticker.upper())
        hist = stock.history(period="1d")
        if not hist.empty:
            current_price = float(hist['Close'].iloc[-1])
        else:
            current_price = float(grant_price)
    except:
        current_price = float(grant_price)

    new_rsu = {
        "id": str(uuid.uuid4()),
        "ticker": ticker.upper(),
        "shares": float(shares),
        "vest_date": vest_date,
        "grant_price": float(grant_price),
        "current_price": current_price
    }
    income_data['rsus'].append(new_rsu)
    save_income(income_data)

    return str(datetime.now())

# Callback: Display RSU holdings
@app.callback(
    Output('rsu-holdings-list', 'children'),
    [Input('income-refresh-trigger', 'data'),
     Input('rsu-refresh-btn', 'n_clicks'),
     Input({'type': 'rsu-delete', 'id': ALL}, 'n_clicks')],
    prevent_initial_call=False
)
def display_rsu_holdings(refresh, refresh_clicks, delete_clicks):
    ctx = callback_context
    income_data = load_income()

    # Handle delete
    if ctx.triggered and 'rsu-delete' in ctx.triggered[0]['prop_id']:
        import ast
        trigger_dict = ast.literal_eval(ctx.triggered[0]['prop_id'].split('.')[0])
        rsu_id = trigger_dict['id']
        income_data['rsus'] = [r for r in income_data['rsus'] if r['id'] != rsu_id]
        save_income(income_data)

    # Handle refresh prices
    if ctx.triggered and 'rsu-refresh-btn' in ctx.triggered[0]['prop_id']:
        for rsu in income_data['rsus']:
            try:
                stock = yf.Ticker(rsu['ticker'])
                hist = stock.history(period="1d")
                if not hist.empty:
                    rsu['current_price'] = float(hist['Close'].iloc[-1])
            except:
                pass
        save_income(income_data)

    rsus = income_data.get('rsus', [])

    if not rsus:
        return html.P("No RSU holdings added.", style={"color": "#888"})

    rows = []
    total_value = 0
    total_gain = 0

    for rsu in rsus:
        current_price = rsu.get('current_price', rsu['grant_price'])
        shares = rsu['shares']
        value = current_price * shares
        cost = rsu['grant_price'] * shares
        gain = value - cost
        gain_pct = ((current_price - rsu['grant_price']) / rsu['grant_price'] * 100) if rsu['grant_price'] > 0 else 0

        total_value += value
        total_gain += gain

        gain_color = "#2e7d32" if gain >= 0 else "#dc3545"
        gain_text = f"+${gain:,.2f} ({gain_pct:+.1f}%)" if gain >= 0 else f"-${abs(gain):,.2f} ({gain_pct:.1f}%)"

        rows.append(html.Tr([
            html.Td(html.Span(rsu['ticker'], style={"fontWeight": "700", "color": "#1a73e8"})),
            html.Td(f"{shares:,.2f}"),
            html.Td(f"${rsu['grant_price']:,.2f}"),
            html.Td(f"${current_price:,.2f}"),
            html.Td(f"${value:,.2f}", style={"fontWeight": "600"}),
            html.Td(gain_text, style={"color": gain_color, "fontWeight": "600"}),
            html.Td(rsu['vest_date']),
            html.Td(dbc.Button(html.I(className="fas fa-trash"), id={'type': 'rsu-delete', 'id': rsu['id']},
                              color="link", size="sm", style={"color": "#dc3545"}))
        ]))

    # Add total row
    total_gain_color = "#2e7d32" if total_gain >= 0 else "#dc3545"
    rows.append(html.Tr([
        html.Td(html.Strong("TOTAL"), colSpan=4),
        html.Td(html.Strong(f"${total_value:,.2f}")),
        html.Td(html.Strong(f"${total_gain:+,.2f}"), style={"color": total_gain_color}),
        html.Td(""),
        html.Td("")
    ], style={"backgroundColor": "#f8f9fa"}))

    return html.Table([
        html.Thead(html.Tr([html.Th("Ticker"), html.Th("Shares"), html.Th("Grant $"),
                           html.Th("Current $"), html.Th("Value"), html.Th("Gain/Loss"),
                           html.Th("Vest Date"), html.Th("")])),
        html.Tbody(rows)
    ], className="table", style={"width": "100%"})

# Callback: Income history with filtering
@app.callback(
    [Output('income-history-container', 'children'),
     Output('income-count-display', 'children'),
     Output('income-monthly-summary', 'children')],
    [Input('income-filter-month', 'value'),
     Input('income-filter-type', 'value'),
     Input('income-filter-search', 'value'),
     Input('income-refresh-trigger', 'data'),
     Input({'type': 'income-delete', 'id': ALL}, 'n_clicks')],
    prevent_initial_call=False
)
def update_income_history(filter_month, filter_type, filter_search, refresh, delete_clicks):
    ctx = callback_context
    income_data = load_income()

    # Handle delete
    if ctx.triggered and 'income-delete' in ctx.triggered[0]['prop_id']:
        import ast
        trigger_dict = ast.literal_eval(ctx.triggered[0]['prop_id'].split('.')[0])
        income_id = trigger_dict['id']
        income_data['income'] = [i for i in income_data['income'] if i['id'] != income_id]
        save_income(income_data)

    incomes = income_data.get('income', [])

    # Apply filters
    filtered = incomes

    if filter_month and filter_month != 'ALL':
        filtered = [i for i in filtered if i.get('date', '').startswith(filter_month)]

    if filter_type and filter_type != 'ALL':
        filtered = [i for i in filtered if i.get('type') == filter_type]

    if filter_search:
        filtered = [i for i in filtered if filter_search.lower() in i.get('source', '').lower()]

    # Sort by date descending
    filtered = sorted(filtered, key=lambda x: x.get('date', ''), reverse=True)

    count_text = f"Showing {len(filtered)} of {len(incomes)} entries"

    # Build history table
    if not filtered:
        history = html.P("No income entries found.", style={"color": "#888", "padding": "20px", "textAlign": "center"})
    else:
        rows = []
        for i in filtered[:100]:
            type_color = INCOME_TYPE_COLORS.get(i.get('type', 'OTHER'), '#888')
            type_label = INCOME_TYPE_LABELS.get(i.get('type', 'OTHER'), i.get('type', 'Other'))

            rows.append(html.Tr([
                html.Td(i['date'], style={"fontSize": "0.9rem"}),
                html.Td([
                    html.Span(type_label, style={
                        "backgroundColor": f"{type_color}22",
                        "color": type_color,
                        "padding": "3px 10px",
                        "borderRadius": "12px",
                        "fontSize": "0.8rem",
                        "fontWeight": "600"
                    })
                ]),
                html.Td(i['source'], style={"fontSize": "0.9rem"}),
                html.Td(f"${i['amount']:,.2f}", style={"color": "#2e7d32", "fontWeight": "600", "fontSize": "0.9rem"}),
                html.Td(dbc.Button(html.I(className="fas fa-trash"), id={'type': 'income-delete', 'id': i['id']},
                                  color="link", size="sm", style={"color": "#dc3545"}))
            ]))

        history = html.Table([
            html.Thead(html.Tr([
                html.Th("Date", style={"width": "100px"}),
                html.Th("Type", style={"width": "120px"}),
                html.Th("Source"),
                html.Th("Amount", style={"width": "120px"}),
                html.Th("", style={"width": "50px"})
            ], style={"fontSize": "0.85rem", "color": "#666"})),
            html.Tbody(rows)
        ], className="table table-hover", style={"width": "100%"})

    # Build monthly summary
    monthly_totals = {}
    for i in incomes:
        month = i.get('date', '')[:7]
        if month:
            if month not in monthly_totals:
                monthly_totals[month] = {'total': 0, 'types': {}}
            monthly_totals[month]['total'] += i.get('amount', 0)
            t = i.get('type', 'OTHER')
            monthly_totals[month]['types'][t] = monthly_totals[month]['types'].get(t, 0) + i.get('amount', 0)

    if not monthly_totals:
        summary = html.P("No income data for summary.", style={"color": "#888"})
    else:
        sorted_months = sorted(monthly_totals.keys(), reverse=True)[:6]
        summary_rows = []
        for month in sorted_months:
            data = monthly_totals[month]
            try:
                month_label = datetime.strptime(month, "%Y-%m").strftime("%B %Y")
            except:
                month_label = month

            type_pills = []
            for t, amt in sorted(data['types'].items(), key=lambda x: -x[1]):
                color = INCOME_TYPE_COLORS.get(t, '#888')
                label = INCOME_TYPE_LABELS.get(t, t)
                type_pills.append(html.Span(f"{label}: ${amt:,.0f}", style={
                    "backgroundColor": f"{color}22",
                    "color": color,
                    "padding": "2px 8px",
                    "borderRadius": "10px",
                    "fontSize": "0.75rem",
                    "marginRight": "5px"
                }))

            summary_rows.append(html.Tr([
                html.Td(month_label, style={"fontWeight": "600"}),
                html.Td(f"${data['total']:,.2f}", style={"color": "#2e7d32", "fontWeight": "700"}),
                html.Td(type_pills)
            ]))

        summary = html.Table([
            html.Thead(html.Tr([html.Th("Month"), html.Th("Total"), html.Th("Breakdown")])),
            html.Tbody(summary_rows)
        ], className="table", style={"width": "100%"})

    return history, count_text, summary

# ============================================================================
# EXPENSE TRACKING CALLBACKS (Redesigned)
# ============================================================================

# Category colors for consistent styling across expense UI
EXPENSE_CATEGORY_COLORS = {
    "Dining": "#FF6B6B",
    "Shopping": "#4ECDC4",
    "Gas": "#45B7D1",
    "Entertainment": "#96CEB4",
    "Bills": "#FFEAA7",
    "Travel": "#DDA0DD",
    "Subscriptions": "#98D8C8",
    "Other": "#C9C9C9"
}

def parse_capital_one_csv(df):
    """Parse Capital One credit card CSV format"""
    parsed = []

    # Check if this is Capital One format
    required_cols = ['Transaction Date', 'Description', 'Category', 'Debit']
    if not all(col in df.columns for col in required_cols):
        return None  # Not Capital One format

    for _, row in df.iterrows():
        try:
            # Skip Payment/Credit transactions
            if row.get('Category', '') == 'Payment/Credit':
                continue

            # Skip if no Debit amount (these are credits/payments)
            debit_val = row.get('Debit', '')
            if pd.isna(debit_val) or str(debit_val).strip() == '':
                continue

            # Parse date
            date_val = str(row['Transaction Date'])
            try:
                from dateutil import parser as date_parser
                parsed_date = date_parser.parse(date_val)
                date_str = parsed_date.strftime("%Y-%m-%d")
            except:
                date_str = date_val[:10]

            # Get description
            desc = str(row['Description']).strip()

            # Parse amount
            amount = abs(float(str(debit_val).replace('$', '').replace(',', '')))

            # Map category using Capital One category
            original_category = str(row.get('Category', 'Other')).strip()
            mapped_category = CAPITAL_ONE_CATEGORY_MAP.get(original_category, 'Other')

            if amount > 0:
                parsed.append({
                    'date': date_str,
                    'description': desc,
                    'amount': amount,
                    'category': mapped_category,
                    'original_category': original_category
                })
        except Exception as e:
            continue

    return parsed

def parse_bank_csv(df, bank_type='auto'):
    """Parse CSV from different banks - tries Capital One first, then generic"""
    # Try Capital One format first
    capital_one_result = parse_capital_one_csv(df)
    if capital_one_result is not None:
        return capital_one_result

    # Generic parsing (fallback)
    parsed = []
    categories = load_expenses().get('categories', [])

    date_col = None
    desc_col = None
    amount_col = None

    for col in df.columns:
        cl = col.lower()
        if 'date' in cl or 'trans' in cl:
            date_col = col
        if 'desc' in cl or 'merchant' in cl or 'name' in cl or 'memo' in cl:
            desc_col = col
        if 'amount' in cl or 'debit' in cl or 'charge' in cl:
            amount_col = col

    if not all([date_col, desc_col, amount_col]):
        if len(df.columns) >= 3:
            date_col, desc_col, amount_col = df.columns[0], df.columns[1], df.columns[2]
        else:
            return []

    for _, row in df.iterrows():
        try:
            date_val = str(row[date_col])
            try:
                from dateutil import parser as date_parser
                parsed_date = date_parser.parse(date_val)
                date_str = parsed_date.strftime("%Y-%m-%d")
            except:
                date_str = date_val[:10]

            desc = str(row[desc_col])
            amount_str = str(row[amount_col]).replace('$', '').replace(',', '').replace('(', '-').replace(')', '')
            amount = abs(float(amount_str))

            category = auto_categorize(desc, categories)

            if amount > 0:
                parsed.append({
                    'date': date_str,
                    'description': desc,
                    'amount': amount,
                    'category': category
                })
        except:
            continue

    return parsed

def auto_categorize(description, categories):
    """Auto-categorize expense based on description keywords"""
    desc_lower = description.lower()

    keywords = {
        'Dining': ['restaurant', 'cafe', 'coffee', 'doordash', 'uber eats', 'grubhub', 'mcdonald', 'starbucks',
                   'chipotle', 'pizza', 'food', 'deli', 'bakery', 'grill', 'kitchen', 'taco', 'burger', 'sushi'],
        'Shopping': ['amazon', 'ebay', 'etsy', 'walmart', 'target', 'best buy', 'apple', 'clothing', 'shoes',
                    'trader joe', 'safeway', 'grocery', 'costco', 'whole foods', 'merchandise', 'store', 'market'],
        'Gas': ['shell', 'exxon', 'chevron', 'bp ', 'gas', 'fuel', 'speedway', 'arco', 'gasoline', 'automotive'],
        'Entertainment': ['netflix', 'spotify', 'hulu', 'disney', 'amazon prime', 'movie', 'theater', 'concert',
                         'game', 'playstation', 'xbox', 'ticketmaster', 'golf', 'badminton', 'sports'],
        'Bills': ['electric', 'water', 'utility', 'internet', 'phone', 'at&t', 'verizon', 't-mobile', 'comcast',
                 'insurance', 'rent', 'mortgage', 'service'],
        'Travel': ['airline', 'hotel', 'airbnb', 'uber', 'lyft', 'parking', 'toll', 'flight', 'southwest',
                  'delta', 'united', 'caltrain', 'transit', 'airfare', 'air france'],
        'Subscriptions': ['subscription', 'membership', 'annual', 'monthly', 'paramount', 'cable']
    }

    for category, kws in keywords.items():
        if category in categories:
            for kw in kws:
                if kw in desc_lower:
                    return category

    return 'Other'

def get_expense_hash(expense):
    """Generate a hash for duplicate detection"""
    return f"{expense.get('date', '')}|{expense.get('description', '').lower()[:50]}|{expense.get('amount', 0):.2f}"

def find_duplicates(new_expenses, existing_expenses):
    """Find potential duplicates between new and existing expenses"""
    existing_hashes = {get_expense_hash(e) for e in existing_expenses}
    duplicates = []
    unique = []

    for exp in new_expenses:
        if get_expense_hash(exp) in existing_hashes:
            duplicates.append(exp)
        else:
            unique.append(exp)

    return unique, duplicates

# Callback: Tab switching for Add/Import
@app.callback(
    [Output('add-expense-form', 'style'),
     Output('import-csv-form', 'style')],
    Input('expense-input-tabs', 'active_tab'),
    prevent_initial_call=False
)
def toggle_expense_input_tabs(active_tab):
    if active_tab == 'tab-add-expense':
        return {"display": "block"}, {"display": "none"}
    else:
        return {"display": "none"}, {"display": "block"}

# Callback: Month navigation and overview
@app.callback(
    [Output('expense-selected-month', 'data'),
     Output('expense-month-display', 'children'),
     Output('expense-total-spent', 'children'),
     Output('expense-vs-budget', 'children'),
     Output('expense-vs-budget', 'style'),
     Output('expense-vs-last-month', 'children'),
     Output('expense-vs-last-month', 'style'),
     Output('expense-category-pills', 'children'),
     Output('budget-month-selector', 'options'),
     Output('budget-month-selector', 'value'),
     Output('expense-filter-month', 'options')],
    [Input('expense-month-prev', 'n_clicks'),
     Input('expense-month-next', 'n_clicks'),
     Input('expense-refresh-trigger', 'children')],
    [State('expense-selected-month', 'data')],
    prevent_initial_call=False
)
def update_expense_overview(prev_clicks, next_clicks, refresh, current_month):
    ctx = callback_context
    expenses_data = load_expenses()
    expenses = expenses_data.get('expenses', [])
    budgets = expenses_data.get('budgets', {})

    # Handle month navigation
    if current_month is None:
        current_month = datetime.now().strftime("%Y-%m")

    if ctx.triggered:
        trigger = ctx.triggered[0]['prop_id']
        if 'expense-month-prev' in trigger:
            dt = datetime.strptime(current_month, "%Y-%m")
            dt = dt - relativedelta(months=1)
            current_month = dt.strftime("%Y-%m")
        elif 'expense-month-next' in trigger:
            dt = datetime.strptime(current_month, "%Y-%m")
            dt = dt + relativedelta(months=1)
            current_month = dt.strftime("%Y-%m")

    # Format month display
    try:
        month_dt = datetime.strptime(current_month, "%Y-%m")
        month_display = month_dt.strftime("%B %Y")
    except:
        month_display = current_month

    # Calculate totals for selected month
    month_expenses = [e for e in expenses if e.get('date', '').startswith(current_month)]
    total_spent = sum(e.get('amount', 0) for e in month_expenses)

    # Calculate previous month
    try:
        prev_month_dt = datetime.strptime(current_month, "%Y-%m") - relativedelta(months=1)
        prev_month = prev_month_dt.strftime("%Y-%m")
    except:
        prev_month = current_month

    prev_month_expenses = [e for e in expenses if e.get('date', '').startswith(prev_month)]
    prev_total = sum(e.get('amount', 0) for e in prev_month_expenses)

    # Budget comparison
    month_budget = budgets.get(current_month, {})
    total_budget = sum(month_budget.values()) if month_budget else 0

    if total_budget > 0:
        budget_pct = (total_spent / total_budget) * 100
        if budget_pct <= 80:
            budget_color = "#2e7d32"
        elif budget_pct <= 100:
            budget_color = "#f57c00"
        else:
            budget_color = "#dc3545"
        vs_budget = f"{budget_pct:.0f}%"
        vs_budget_style = {"margin": "0", "fontWeight": "700", "color": budget_color}
    else:
        vs_budget = "No budget"
        vs_budget_style = {"margin": "0", "fontWeight": "700", "color": "#888"}

    # vs Last Month
    if prev_total > 0:
        change_pct = ((total_spent - prev_total) / prev_total) * 100
        if change_pct > 0:
            vs_last = f"+{change_pct:.0f}%"
            vs_last_style = {"margin": "0", "fontWeight": "700", "color": "#dc3545"}
        else:
            vs_last = f"{change_pct:.0f}%"
            vs_last_style = {"margin": "0", "fontWeight": "700", "color": "#2e7d32"}
    else:
        vs_last = "N/A"
        vs_last_style = {"margin": "0", "fontWeight": "700", "color": "#888"}

    # Category pills
    cat_totals = {}
    for e in month_expenses:
        c = e.get('category', 'Other')
        cat_totals[c] = cat_totals.get(c, 0) + e.get('amount', 0)

    pills = []
    for cat, amount in sorted(cat_totals.items(), key=lambda x: -x[1]):
        color = EXPENSE_CATEGORY_COLORS.get(cat, "#888")
        pills.append(html.Div([
            html.Span(cat, style={"fontWeight": "600", "marginRight": "5px"}),
            html.Span(f"${amount:,.0f}", style={"color": "#666"})
        ], style={
            "backgroundColor": f"{color}22",
            "border": f"1px solid {color}",
            "borderRadius": "20px",
            "padding": "5px 15px",
            "fontSize": "0.85rem"
        }))

    # Build month options for dropdowns
    all_months = sorted(set(e.get('date', '')[:7] for e in expenses if e.get('date')), reverse=True)
    if current_month not in all_months:
        all_months = [current_month] + all_months

    month_options = [{"label": datetime.strptime(m, "%Y-%m").strftime("%B %Y"), "value": m} for m in all_months[:24]]
    filter_month_options = [{"label": "All Months", "value": "ALL"}] + month_options

    return (current_month, month_display, f"${total_spent:,.2f}", vs_budget, vs_budget_style,
            vs_last, vs_last_style, pills, month_options, current_month, filter_month_options)

# Callback: Budget progress bars
@app.callback(
    Output('budget-progress-container', 'children'),
    [Input('budget-month-selector', 'value'),
     Input({'type': 'budget-save', 'category': ALL}, 'n_clicks'),
     Input('budget-copy-prev-btn', 'n_clicks')],
    [State({'type': 'budget-input', 'category': ALL}, 'value'),
     State({'type': 'budget-input', 'category': ALL}, 'id')],
    prevent_initial_call=False
)
def update_budget_progress(selected_month, save_clicks, copy_clicks, budget_values, budget_ids):
    ctx = callback_context
    expenses_data = load_expenses()
    expenses = expenses_data.get('expenses', [])
    budgets = expenses_data.get('budgets', {})
    categories = expenses_data.get('categories', [])

    if selected_month is None:
        selected_month = datetime.now().strftime("%Y-%m")

    # Handle copy from previous month
    if ctx.triggered and 'budget-copy-prev-btn' in ctx.triggered[0]['prop_id']:
        try:
            prev_month_dt = datetime.strptime(selected_month, "%Y-%m") - relativedelta(months=1)
            prev_month = prev_month_dt.strftime("%Y-%m")
            if prev_month in budgets:
                budgets[selected_month] = budgets[prev_month].copy()
                expenses_data['budgets'] = budgets
                save_expenses(expenses_data)
        except:
            pass

    # Handle budget saves
    if ctx.triggered and 'budget-save' in ctx.triggered[0]['prop_id']:
        if budget_values and budget_ids:
            if selected_month not in budgets:
                budgets[selected_month] = {}
            for val, id_obj in zip(budget_values, budget_ids):
                if val is not None and val > 0:
                    budgets[selected_month][id_obj['category']] = float(val)
            expenses_data['budgets'] = budgets
            save_expenses(expenses_data)

    # Calculate spending by category for selected month
    month_expenses = [e for e in expenses if e.get('date', '').startswith(selected_month)]
    cat_spent = {}
    for e in month_expenses:
        c = e.get('category', 'Other')
        cat_spent[c] = cat_spent.get(c, 0) + e.get('amount', 0)

    month_budgets = budgets.get(selected_month, {})

    # Build progress bars
    rows = []
    for cat in categories:
        spent = cat_spent.get(cat, 0)
        budget = month_budgets.get(cat, 0)
        color = EXPENSE_CATEGORY_COLORS.get(cat, "#888")

        if budget > 0:
            pct = min((spent / budget) * 100, 100)
            if pct <= 80:
                bar_color = "#2e7d32"
            elif pct <= 100:
                bar_color = "#f57c00"
            else:
                bar_color = "#dc3545"
            status_text = f"${spent:,.0f} / ${budget:,.0f}"
            over_budget = spent > budget
        else:
            pct = 0
            bar_color = "#e0e0e0"
            status_text = f"${spent:,.0f} spent" if spent > 0 else "No spending"
            over_budget = False

        rows.append(dbc.Row([
            dbc.Col([
                html.Div([
                    html.Span(cat, style={"fontWeight": "600", "color": color})
                ])
            ], width=2),
            dbc.Col([
                html.Div([
                    html.Div(style={
                        "width": f"{pct}%",
                        "height": "24px",
                        "backgroundColor": bar_color,
                        "borderRadius": "12px",
                        "transition": "width 0.3s ease"
                    })
                ], style={
                    "width": "100%",
                    "height": "24px",
                    "backgroundColor": "#f0f0f0",
                    "borderRadius": "12px",
                    "overflow": "hidden"
                })
            ], width=5),
            dbc.Col([
                html.Span(status_text, style={
                    "fontSize": "0.9rem",
                    "fontWeight": "600" if over_budget else "normal",
                    "color": "#dc3545" if over_budget else "#666"
                })
            ], width=2),
            dbc.Col([
                dbc.InputGroup([
                    dbc.InputGroupText("$", style={"fontSize": "0.85rem"}),
                    dbc.Input(
                        id={'type': 'budget-input', 'category': cat},
                        type="number",
                        value=budget if budget > 0 else None,
                        placeholder="Set...",
                        style={"fontSize": "0.85rem"},
                        size="sm"
                    ),
                    dbc.Button("Save", id={'type': 'budget-save', 'category': cat},
                              color="primary", size="sm", style={"fontSize": "0.8rem"})
                ], size="sm")
            ], width=3),
        ], style={"marginBottom": "12px", "alignItems": "center"}))

    return html.Div(rows)

# Callback: Charts
@app.callback(
    [Output('expense-pie-chart', 'figure'),
     Output('expense-bar-chart', 'figure')],
    [Input('expense-selected-month', 'data'),
     Input('expense-refresh-trigger', 'children')],
    prevent_initial_call=False
)
def update_expense_charts(selected_month, refresh):
    expenses_data = load_expenses()
    expenses = expenses_data.get('expenses', [])

    if selected_month is None:
        selected_month = datetime.now().strftime("%Y-%m")

    # Filter for selected month
    month_expenses = [e for e in expenses if e.get('date', '').startswith(selected_month)]

    # Pie chart by category
    cat_totals = {}
    for e in month_expenses:
        c = e.get('category', 'Other')
        cat_totals[c] = cat_totals.get(c, 0) + e.get('amount', 0)

    if cat_totals:
        colors = [EXPENSE_CATEGORY_COLORS.get(c, "#888") for c in cat_totals.keys()]
        pie_fig = go.Figure(data=[go.Pie(
            labels=list(cat_totals.keys()),
            values=list(cat_totals.values()),
            hole=0.45,
            marker_colors=colors,
            textinfo='label+percent',
            textposition='outside'
        )])
        pie_fig.update_layout(
            margin=dict(l=20, r=20, t=30, b=20),
            height=280,
            showlegend=False,
            font=dict(size=11)
        )
    else:
        pie_fig = go.Figure()
        pie_fig.add_annotation(text="No expense data", x=0.5, y=0.5, showarrow=False, font=dict(size=14, color="#888"))
        pie_fig.update_layout(height=280, margin=dict(l=20, r=20, t=30, b=20))

    # Monthly trend bar chart (last 4 months)
    monthly_data = {}
    for e in expenses:
        month = e.get('date', '')[:7]
        if month:
            monthly_data[month] = monthly_data.get(month, 0) + e.get('amount', 0)

    if monthly_data:
        sorted_months = sorted(monthly_data.keys())[-4:]  # Only 4 months
        month_labels = [datetime.strptime(m, "%Y-%m").strftime("%b '%y") for m in sorted_months]
        colors = ['#1a73e8' if m != selected_month else '#dc3545' for m in sorted_months]

        # Calculate y-axis range with padding
        max_val = max(monthly_data[m] for m in sorted_months)
        y_max = max_val * 1.15  # 15% padding for text labels

        bar_fig = go.Figure(data=[go.Bar(
            x=month_labels,
            y=[monthly_data[m] for m in sorted_months],
            marker_color=colors,
            text=[f"${monthly_data[m]:,.0f}" for m in sorted_months],
            textposition='outside',
            customdata=sorted_months,  # Store actual month values for click handling
            hovertemplate='%{x}<br>$%{y:,.2f}<extra></extra>'
        )])
        bar_fig.update_layout(
            margin=dict(l=50, r=20, t=30, b=40),
            height=280,
            yaxis=dict(
                tickprefix='$',
                tickformat=',',
                range=[0, y_max],
                automargin=True
            ),
            xaxis=dict(
                tickangle=0
            ),
            showlegend=False,
            font=dict(size=11),
            bargap=0.3
        )
    else:
        bar_fig = go.Figure()
        bar_fig.add_annotation(text="No expense data", x=0.5, y=0.5, showarrow=False, font=dict(size=14, color="#888"))
        bar_fig.update_layout(height=280, margin=dict(l=20, r=20, t=30, b=20))

    return pie_fig, bar_fig

# Callback: Handle bar chart click to filter by month
@app.callback(
    [Output('expense-selected-month', 'data', allow_duplicate=True),
     Output('expense-filter-month', 'value')],
    Input('expense-bar-chart', 'clickData'),
    State('expense-selected-month', 'data'),
    prevent_initial_call=True
)
def handle_bar_chart_click(click_data, current_month):
    if click_data and 'points' in click_data:
        point = click_data['points'][0]
        if 'customdata' in point:
            clicked_month = point['customdata']
            return clicked_month, clicked_month
    raise PreventUpdate

# Callback: Add expense manually
@app.callback(
    Output('expense-refresh-trigger', 'children', allow_duplicate=True),
    Input('expense-add-btn', 'n_clicks'),
    [State('expense-date', 'value'),
     State('expense-desc', 'value'),
     State('expense-amount', 'value'),
     State('expense-category', 'value')],
    prevent_initial_call=True
)
def add_expense_manually(n_clicks, expense_date, desc, amount, category):
    if not all([expense_date, desc, amount, category]):
        raise PreventUpdate

    expenses_data = load_expenses()
    new_expense = {
        "id": str(uuid.uuid4()),
        "date": expense_date,
        "description": desc,
        "amount": float(amount),
        "category": category,
        "imported_from": None
    }
    expenses_data['expenses'].append(new_expense)
    save_expenses(expenses_data)

    return str(datetime.now())  # Trigger refresh

# Callback: CSV Upload preview
@app.callback(
    [Output('expense-csv-preview', 'children'),
     Output('expense-csv-data-store', 'data')],
    Input('expense-csv-upload', 'contents'),
    State('expense-csv-upload', 'filename'),
    prevent_initial_call=True
)
def handle_expense_csv_upload(contents, filename):
    if not contents:
        return html.Div(), None

    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))

        # Parse the CSV
        parsed = parse_bank_csv(df, 'auto')

        if not parsed:
            return dbc.Alert("Could not parse CSV. Please check the format.", color="warning"), None

        # Check for duplicates
        expenses_data = load_expenses()
        existing_expenses = expenses_data.get('expenses', [])
        unique, duplicates = find_duplicates(parsed, existing_expenses)

        # Build preview table
        preview_rows = []
        for row in parsed[:15]:
            is_dup = row in duplicates
            row_style = {"backgroundColor": "#fff3cd"} if is_dup else {}
            preview_rows.append(html.Tr([
                html.Td(row['date'], style={"fontSize": "0.85rem"}),
                html.Td(row['description'][:35] + ('...' if len(row['description']) > 35 else ''),
                       style={"fontSize": "0.85rem"}),
                html.Td(f"${row['amount']:,.2f}", style={"fontSize": "0.85rem", "fontWeight": "600"}),
                html.Td(row['category'], style={"fontSize": "0.85rem"}),
                html.Td("Duplicate" if is_dup else "", style={"fontSize": "0.75rem", "color": "#856404"})
            ], style=row_style))

        # Build preview UI
        preview_content = [
            html.H5(f"Preview: {filename}", style={"marginBottom": "10px", "color": "#1a73e8"}),
            html.P(f"Found {len(parsed)} transactions ({len(unique)} new, {len(duplicates)} potential duplicates)",
                  style={"color": "#666", "fontSize": "0.9rem"}),
        ]

        if duplicates:
            preview_content.append(
                dbc.Alert([
                    html.I(className="fas fa-exclamation-triangle", style={"marginRight": "10px"}),
                    f"{len(duplicates)} potential duplicates found (highlighted in yellow). Choose how to proceed:"
                ], color="warning", style={"fontSize": "0.9rem"})
            )

        preview_content.extend([
            html.Table([
                html.Thead(html.Tr([
                    html.Th("Date"), html.Th("Description"), html.Th("Amount"), html.Th("Category"), html.Th("")
                ], style={"fontSize": "0.85rem", "color": "#666"})),
                html.Tbody(preview_rows)
            ], className="table", style={"fontSize": "0.9rem", "marginBottom": "15px"}),
            html.P(f"Showing first 15 of {len(parsed)} transactions" if len(parsed) > 15 else "",
                  style={"color": "#888", "fontSize": "0.8rem"}),
            html.Div([
                dbc.Button(f"Import All ({len(parsed)})", id={'type': 'expense-csv-import', 'mode': 'all'},
                          color="primary", style={"marginRight": "10px"}),
                dbc.Button(f"Import New Only ({len(unique)})", id={'type': 'expense-csv-import', 'mode': 'unique'},
                          color="success", style={"marginRight": "10px"}) if duplicates else None,
                dbc.Button("Cancel", id={'type': 'expense-csv-import', 'mode': 'cancel'},
                          color="secondary", outline=True)
            ], style={"marginTop": "15px"})
        ])

        return html.Div(preview_content), {
            'contents': contents,
            'filename': filename,
            'parsed': parsed,
            'unique': unique,
            'duplicates': duplicates
        }

    except Exception as e:
        return dbc.Alert(f"Error parsing CSV: {str(e)}", color="danger"), None

# Callback: CSV Import confirmation
@app.callback(
    [Output('expense-csv-preview', 'children', allow_duplicate=True),
     Output('expense-refresh-trigger', 'children', allow_duplicate=True)],
    Input({'type': 'expense-csv-import', 'mode': ALL}, 'n_clicks'),
    State('expense-csv-data-store', 'data'),
    prevent_initial_call=True
)
def handle_expense_csv_import(n_clicks_list, stored_data):
    ctx = callback_context

    if not any(n_clicks_list) or not stored_data:
        raise PreventUpdate

    # Find which button was clicked
    trigger = ctx.triggered[0]['prop_id']

    if 'cancel' in trigger:
        return html.Div(), None

    mode = 'all' if 'all' in trigger else 'unique'

    expenses_data = load_expenses()

    if mode == 'all':
        to_import = stored_data['parsed']
    else:
        to_import = stored_data['unique']

    filename = stored_data['filename']

    for row in to_import:
        new_expense = {
            "id": str(uuid.uuid4()),
            "date": row['date'],
            "description": row['description'],
            "amount": row['amount'],
            "category": row['category'],
            "imported_from": filename
        }
        expenses_data['expenses'].append(new_expense)

    save_expenses(expenses_data)

    success_msg = html.Div([
        html.Div([
            html.I(className="fas fa-check-circle", style={"color": "#28a745", "fontSize": "2rem", "marginRight": "15px"}),
            html.Span(f"Successfully imported {len(to_import)} transactions!",
                     style={"fontSize": "1.1rem", "fontWeight": "600", "color": "#28a745"})
        ], style={"display": "flex", "alignItems": "center"})
    ], style={"padding": "20px", "backgroundColor": "#d4edda", "borderRadius": "10px"})

    return success_msg, str(datetime.now())

# Callback: Transaction history with filtering, sorting, and inline editing
@app.callback(
    [Output('expense-history-container', 'children'),
     Output('expense-count-display', 'children')],
    [Input('expense-filter-month', 'value'),
     Input('expense-filter-category', 'value'),
     Input('expense-filter-search', 'value'),
     Input('expense-sort-by', 'value'),
     Input('expense-refresh-trigger', 'children'),
     Input({'type': 'expense-delete', 'id': ALL}, 'n_clicks'),
     Input('expense-editing-row-id', 'data')],
    prevent_initial_call=False
)
def update_expense_history(filter_month, filter_categories, filter_search, sort_by, refresh, delete_clicks, editing_id):
    ctx = callback_context
    expenses_data = load_expenses()
    categories = expenses_data.get('categories', [])

    # Handle delete
    if ctx.triggered and 'expense-delete' in ctx.triggered[0]['prop_id']:
        import ast
        trigger_dict = ast.literal_eval(ctx.triggered[0]['prop_id'].split('.')[0])
        expense_id = trigger_dict['id']
        expenses_data['expenses'] = [e for e in expenses_data['expenses'] if e['id'] != expense_id]
        save_expenses(expenses_data)

    expenses = expenses_data.get('expenses', [])

    # Apply filters
    filtered = expenses

    if filter_month and filter_month != 'ALL':
        filtered = [e for e in filtered if e.get('date', '').startswith(filter_month)]

    if filter_categories and filter_categories != 'ALL':
        if isinstance(filter_categories, list):
            filtered = [e for e in filtered if e.get('category') in filter_categories]
        else:
            filtered = [e for e in filtered if e.get('category') == filter_categories]

    if filter_search:
        filtered = [e for e in filtered if filter_search.lower() in e.get('description', '').lower()]

    # Apply sorting
    if sort_by == 'date-desc':
        filtered = sorted(filtered, key=lambda x: x.get('date', ''), reverse=True)
    elif sort_by == 'date-asc':
        filtered = sorted(filtered, key=lambda x: x.get('date', ''))
    elif sort_by == 'amount-desc':
        filtered = sorted(filtered, key=lambda x: x.get('amount', 0), reverse=True)
    elif sort_by == 'amount-asc':
        filtered = sorted(filtered, key=lambda x: x.get('amount', 0))
    elif sort_by == 'category':
        filtered = sorted(filtered, key=lambda x: x.get('category', ''))

    count_text = f"Showing {len(filtered)} of {len(expenses)} transactions"

    if not filtered:
        return html.P("No transactions found.", style={"color": "#888", "padding": "20px", "textAlign": "center"}), count_text

    # Build table rows with inline editing capability (limit to 100)
    rows = []
    for e in filtered[:100]:
        cat_color = EXPENSE_CATEGORY_COLORS.get(e.get('category', 'Other'), '#888')
        is_editing = editing_id == e['id']

        if is_editing:
            # Editing mode - show input fields
            rows.append(html.Tr([
                html.Td(
                    dbc.Input(id={'type': 'inline-edit-date', 'id': e['id']},
                             type="date", value=e['date'], size="sm",
                             style={"fontSize": "0.85rem", "padding": "4px 8px"}),
                    style={"verticalAlign": "middle"}
                ),
                html.Td(
                    dbc.Input(id={'type': 'inline-edit-desc', 'id': e['id']},
                             value=e['description'], size="sm",
                             style={"fontSize": "0.85rem", "padding": "4px 8px"}),
                    style={"verticalAlign": "middle"}
                ),
                html.Td(
                    dcc.Dropdown(id={'type': 'inline-edit-cat', 'id': e['id']},
                                options=[{"label": c, "value": c} for c in categories],
                                value=e.get('category', 'Other'),
                                clearable=False,
                                style={"fontSize": "0.85rem", "minWidth": "100px"}),
                    style={"verticalAlign": "middle"}
                ),
                html.Td(
                    dbc.Input(id={'type': 'inline-edit-amount', 'id': e['id']},
                             type="number", value=e['amount'], size="sm", step="0.01",
                             style={"fontSize": "0.85rem", "padding": "4px 8px", "width": "90px"}),
                    style={"verticalAlign": "middle"}
                ),
                html.Td([
                    dbc.Button(html.I(className="fas fa-check"), id={'type': 'inline-edit-save', 'id': e['id']},
                              color="success", size="sm", style={"padding": "4px 8px", "marginRight": "5px"}),
                    dbc.Button(html.I(className="fas fa-times"), id={'type': 'inline-edit-cancel', 'id': e['id']},
                              color="secondary", size="sm", style={"padding": "4px 8px"})
                ], style={"whiteSpace": "nowrap", "verticalAlign": "middle"})
            ], style={"backgroundColor": "#fff3cd"}))
        else:
            # Normal display mode
            rows.append(html.Tr([
                html.Td(e['date'], style={"fontSize": "0.9rem", "verticalAlign": "middle"}),
                html.Td(e['description'][:45] + ('...' if len(e.get('description', '')) > 45 else ''),
                       style={"fontSize": "0.9rem", "verticalAlign": "middle"}),
                html.Td([
                    html.Span(e.get('category', 'Other'), style={
                        "backgroundColor": f"{cat_color}22",
                        "color": cat_color,
                        "padding": "3px 10px",
                        "borderRadius": "12px",
                        "fontSize": "0.8rem",
                        "fontWeight": "600"
                    })
                ], style={"verticalAlign": "middle"}),
                html.Td(f"${e['amount']:,.2f}", style={"color": "#dc3545", "fontWeight": "600", "fontSize": "0.9rem", "verticalAlign": "middle"}),
                html.Td([
                    dbc.Button(html.I(className="fas fa-edit"), id={'type': 'expense-edit-start', 'id': e['id']},
                              color="link", size="sm", style={"padding": "2px 8px"}),
                    dbc.Button(html.I(className="fas fa-trash"), id={'type': 'expense-delete', 'id': e['id']},
                              color="link", size="sm", style={"padding": "2px 8px", "color": "#dc3545"})
                ], style={"whiteSpace": "nowrap", "verticalAlign": "middle"})
            ]))

    table = html.Table([
        html.Thead(html.Tr([
            html.Th("Date", style={"width": "110px"}),
            html.Th("Description"),
            html.Th("Category", style={"width": "130px"}),
            html.Th("Amount", style={"width": "100px"}),
            html.Th("", style={"width": "90px"})
        ], style={"fontSize": "0.85rem", "color": "#666"})),
        html.Tbody(rows)
    ], className="table table-hover", style={"width": "100%"})

    return table, count_text

# Callback: Start inline editing
@app.callback(
    Output('expense-editing-row-id', 'data'),
    [Input({'type': 'expense-edit-start', 'id': ALL}, 'n_clicks'),
     Input({'type': 'inline-edit-cancel', 'id': ALL}, 'n_clicks'),
     Input({'type': 'inline-edit-save', 'id': ALL}, 'n_clicks')],
    prevent_initial_call=True
)
def handle_inline_edit_state(start_clicks, cancel_clicks, save_clicks):
    ctx = callback_context

    if not ctx.triggered:
        raise PreventUpdate

    trigger = ctx.triggered[0]['prop_id']

    # Cancel or save - close editing
    if 'inline-edit-cancel' in trigger or 'inline-edit-save' in trigger:
        return None

    # Start editing
    if 'expense-edit-start' in trigger:
        import ast
        trigger_dict = ast.literal_eval(trigger.split('.')[0])
        return trigger_dict['id']

    raise PreventUpdate

# Callback: Save inline edit
@app.callback(
    Output('expense-refresh-trigger', 'children', allow_duplicate=True),
    Input({'type': 'inline-edit-save', 'id': ALL}, 'n_clicks'),
    [State({'type': 'inline-edit-date', 'id': ALL}, 'value'),
     State({'type': 'inline-edit-date', 'id': ALL}, 'id'),
     State({'type': 'inline-edit-desc', 'id': ALL}, 'value'),
     State({'type': 'inline-edit-amount', 'id': ALL}, 'value'),
     State({'type': 'inline-edit-cat', 'id': ALL}, 'value')],
    prevent_initial_call=True
)
def save_inline_edit(save_clicks, dates, date_ids, descs, amounts, cats):
    ctx = callback_context

    if not ctx.triggered or not any(save_clicks):
        raise PreventUpdate

    trigger = ctx.triggered[0]['prop_id']

    if 'inline-edit-save' not in trigger:
        raise PreventUpdate

    import ast
    trigger_dict = ast.literal_eval(trigger.split('.')[0])
    expense_id = trigger_dict['id']

    # Find the index of the edited expense
    edit_index = None
    for i, id_obj in enumerate(date_ids):
        if id_obj['id'] == expense_id:
            edit_index = i
            break

    if edit_index is None:
        raise PreventUpdate

    # Get the edited values
    new_date = dates[edit_index]
    new_desc = descs[edit_index]
    new_amount = amounts[edit_index]
    new_cat = cats[edit_index]

    if not all([new_date, new_desc, new_amount, new_cat]):
        raise PreventUpdate

    # Save to file
    expenses_data = load_expenses()
    for e in expenses_data['expenses']:
        if e['id'] == expense_id:
            e['date'] = new_date
            e['description'] = new_desc
            e['amount'] = float(new_amount)
            e['category'] = new_cat
            break
    save_expenses(expenses_data)

    return str(datetime.now())

# ============================================================================
# PORTFOLIO ANALYTICS CALLBACKS
# ============================================================================

@app.callback(
    [Output('allocation-pie-chart', 'figure'),
     Output('target-vs-actual-chart', 'figure'),
     Output('rebalance-container', 'children'),
     Output('performance-metrics-container', 'children'),
     Output('sector-pie-chart', 'figure'),
     Output('top-performers-container', 'children'),
     Output('bottom-performers-container', 'children')],
    Input('url', 'pathname'),
    prevent_initial_call=False
)
def update_analytics(pathname):
    """Update portfolio analytics page"""
    if pathname != '/portfolio/analytics':
        empty_fig = go.Figure()
        return empty_fig, empty_fig, html.Div(), html.Div(), empty_fig, html.Div(), html.Div()

    portfolio = load_portfolio()
    settings = load_settings()
    target_allocs = settings.get('target_allocations', {})
    threshold = settings.get('rebalance_threshold', 5)

    # Gather all holdings with current values
    holdings_data = {}
    total_value = 0

    for account in portfolio.get('accounts', []):
        for holding in account.get('holdings', []):
            ticker = holding['ticker']
            data = get_stock_quick_data(ticker)
            if data:
                value = data['price'] * holding['shares']
                cost = holding['avg_cost'] * holding['shares']
                if ticker in holdings_data:
                    holdings_data[ticker]['value'] += value
                    holdings_data[ticker]['cost'] += cost
                    holdings_data[ticker]['shares'] += holding['shares']
                else:
                    holdings_data[ticker] = {
                        'value': value,
                        'cost': cost,
                        'shares': holding['shares'],
                        'price': data['price'],
                        'change_1m': data.get('change_1m', 0)
                    }
                total_value += value

    # Allocation pie chart
    if holdings_data:
        alloc_fig = go.Figure(data=[go.Pie(
            labels=list(holdings_data.keys()),
            values=[h['value'] for h in holdings_data.values()],
            hole=0.4,
            textposition='outside',
            textinfo='label+percent'
        )])
        alloc_fig.update_layout(
            margin=dict(l=40, r=40, t=40, b=40),
            height=260,
            showlegend=False
        )
    else:
        alloc_fig = go.Figure()
        alloc_fig.add_annotation(text="No holdings", x=0.5, y=0.5, showarrow=False)
        alloc_fig.update_layout(height=260)

    # Target vs Actual chart
    if holdings_data and target_allocs:
        tickers = list(set(list(holdings_data.keys()) + list(target_allocs.keys())))
        actual_pcts = []
        target_pcts = []
        for t in tickers:
            actual = (holdings_data.get(t, {}).get('value', 0) / total_value * 100) if total_value > 0 else 0
            target = target_allocs.get(t, 0)
            actual_pcts.append(actual)
            target_pcts.append(target)

        target_fig = go.Figure(data=[
            go.Bar(name='Actual', x=tickers, y=actual_pcts, marker_color='#1a73e8'),
            go.Bar(name='Target', x=tickers, y=target_pcts, marker_color='#e3f2fd')
        ])
        target_fig.update_layout(barmode='group', margin=dict(l=40, r=20, t=30, b=40), height=260,
                                yaxis_title='%', legend=dict(orientation="h", yanchor="bottom", y=1.02))
    else:
        target_fig = go.Figure()
        target_fig.add_annotation(text="Set targets in Settings", x=0.5, y=0.5, showarrow=False)
        target_fig.update_layout(height=260)

    # Rebalancing suggestions
    if holdings_data and target_allocs and total_value > 0:
        suggestions = []
        for ticker in set(list(holdings_data.keys()) + list(target_allocs.keys())):
            actual_pct = (holdings_data.get(ticker, {}).get('value', 0) / total_value * 100)
            target_pct = target_allocs.get(ticker, 0)
            diff = actual_pct - target_pct

            if abs(diff) > threshold:
                if diff > 0:
                    action = "SELL"
                    action_color = "#dc3545"
                    amount = (diff / 100) * total_value
                else:
                    action = "BUY"
                    action_color = "#2e7d32"
                    amount = abs(diff / 100) * total_value

                suggestions.append(html.Div([
                    html.Span(f"{action} ", style={"color": action_color, "fontWeight": "700"}),
                    html.Span(f"${amount:,.0f} of ", style={"color": "#333"}),
                    html.Span(ticker, style={"color": "#1a73e8", "fontWeight": "600"}),
                    html.Span(f" (Current: {actual_pct:.1f}%, Target: {target_pct:.1f}%)",
                             style={"color": "#666", "fontSize": "0.9rem"})
                ], style={"padding": "10px", "backgroundColor": "#f8fbff", "borderRadius": "8px", "marginBottom": "10px"}))

        rebalance_content = html.Div(suggestions) if suggestions else html.P("Portfolio is within target allocations.", style={"color": "#2e7d32"})
    else:
        rebalance_content = html.P("Set target allocations in Settings to see rebalancing suggestions.", style={"color": "#888"})

    # Performance metrics
    if holdings_data:
        total_cost = sum(h['cost'] for h in holdings_data.values())
        total_gain = total_value - total_cost
        total_pct = (total_gain / total_cost * 100) if total_cost > 0 else 0
        gain_class = "positive" if total_gain >= 0 else "negative"

        metrics_content = html.Div([
            html.Div([
                html.Span("Total Value: ", style={"color": "#666"}),
                html.Span(f"${total_value:,.2f}", style={"fontWeight": "700", "fontSize": "1.2rem"})
            ], style={"marginBottom": "10px"}),
            html.Div([
                html.Span("Total Cost Basis: ", style={"color": "#666"}),
                html.Span(f"${total_cost:,.2f}", style={"fontWeight": "600"})
            ], style={"marginBottom": "10px"}),
            html.Div([
                html.Span("Unrealized Gain/Loss: ", style={"color": "#666"}),
                html.Span(f"{'+'if total_gain>=0 else ''}{total_gain:,.2f} ({total_pct:+.1f}%)",
                         className=gain_class, style={"fontWeight": "700", "fontSize": "1.1rem"})
            ], style={"marginBottom": "10px"}),
            html.Div([
                html.Span("Number of Positions: ", style={"color": "#666"}),
                html.Span(f"{len(holdings_data)}", style={"fontWeight": "600"})
            ])
        ])
    else:
        metrics_content = html.P("No holdings data available.", style={"color": "#888"})

    # Sector pie chart (simplified - would need yfinance sector data)
    sector_fig = go.Figure()
    sector_fig.add_annotation(text="Sector data coming soon", x=0.5, y=0.5, showarrow=False)
    sector_fig.update_layout(height=300)

    # Top/Bottom performers
    if holdings_data:
        sorted_by_perf = sorted(holdings_data.items(), key=lambda x: x[1].get('change_1m', 0), reverse=True)

        top_rows = []
        for ticker, data in sorted_by_perf[:5]:
            pct = data.get('change_1m', 0)
            top_rows.append(html.Div([
                html.Span(ticker, style={"fontWeight": "600", "color": "#1a73e8", "width": "60px", "display": "inline-block"}),
                html.Span(f"+{pct:.2f}%" if pct >= 0 else f"{pct:.2f}%",
                         className="positive" if pct >= 0 else "negative", style={"fontWeight": "600"})
            ], style={"padding": "8px 0", "borderBottom": "1px solid #e3f2fd"}))

        bottom_rows = []
        for ticker, data in sorted_by_perf[-5:]:
            pct = data.get('change_1m', 0)
            bottom_rows.append(html.Div([
                html.Span(ticker, style={"fontWeight": "600", "color": "#1a73e8", "width": "60px", "display": "inline-block"}),
                html.Span(f"+{pct:.2f}%" if pct >= 0 else f"{pct:.2f}%",
                         className="positive" if pct >= 0 else "negative", style={"fontWeight": "600"})
            ], style={"padding": "8px 0", "borderBottom": "1px solid #e3f2fd"}))

        top_content = html.Div(top_rows)
        bottom_content = html.Div(bottom_rows)
    else:
        top_content = html.P("No data", style={"color": "#888"})
        bottom_content = html.P("No data", style={"color": "#888"})

    return alloc_fig, target_fig, rebalance_content, metrics_content, sector_fig, top_content, bottom_content

# ============================================================================
# PRICE ALERTS CALLBACKS
# ============================================================================

@app.callback(
    [Output('triggered-alerts-banner', 'children'),
     Output('active-alerts-container', 'children'),
     Output('alert-history-container', 'children')],
    [Input('alert-add-btn', 'n_clicks'),
     Input({'type': 'alert-delete', 'id': ALL}, 'n_clicks'),
     Input({'type': 'alert-dismiss', 'id': ALL}, 'n_clicks'),
     Input('url', 'pathname')],
    [State('alert-ticker', 'value'),
     State('alert-condition', 'value'),
     State('alert-price', 'value')],
    prevent_initial_call=False
)
def manage_alerts(add_clicks, delete_clicks, dismiss_clicks, pathname,
                  ticker, condition, target_price):
    """Manage price alerts"""
    ctx = callback_context
    alerts_data = load_alerts()

    # Handle add alert
    if ctx.triggered and 'alert-add-btn' in ctx.triggered[0]['prop_id']:
        if all([ticker, condition, target_price]):
            new_alert = {
                "id": str(uuid.uuid4()),
                "ticker": ticker.upper().strip(),
                "type": condition,
                "target_price": float(target_price),
                "created_date": datetime.now().strftime("%Y-%m-%d"),
                "triggered": False,
                "triggered_date": None
            }
            alerts_data['alerts'].append(new_alert)
            save_alerts(alerts_data)

    # Handle delete
    if ctx.triggered and 'alert-delete' in ctx.triggered[0]['prop_id']:
        import ast
        trigger_dict = ast.literal_eval(ctx.triggered[0]['prop_id'].split('.')[0])
        alert_id = trigger_dict['id']
        alerts_data['alerts'] = [a for a in alerts_data['alerts'] if a['id'] != alert_id]
        save_alerts(alerts_data)

    # Handle dismiss
    if ctx.triggered and 'alert-dismiss' in ctx.triggered[0]['prop_id']:
        import ast
        trigger_dict = ast.literal_eval(ctx.triggered[0]['prop_id'].split('.')[0])
        alert_id = trigger_dict['id']
        alerts_data['alerts'] = [a for a in alerts_data['alerts'] if a['id'] != alert_id]
        save_alerts(alerts_data)

    # Check alerts and get current prices
    alerts = alerts_data.get('alerts', [])
    newly_triggered = []

    for alert in alerts:
        if alert['triggered']:
            continue

        try:
            data = get_stock_quick_data(alert['ticker'])
            if data:
                current_price = data['price']
                triggered = False

                if alert['type'] == 'ABOVE' and current_price >= alert['target_price']:
                    triggered = True
                elif alert['type'] == 'BELOW' and current_price <= alert['target_price']:
                    triggered = True

                if triggered:
                    alert['triggered'] = True
                    alert['triggered_date'] = datetime.now().strftime("%Y-%m-%d")
                    newly_triggered.append({
                        'ticker': alert['ticker'],
                        'type': alert['type'],
                        'target': alert['target_price'],
                        'current': current_price
                    })
        except:
            continue

    if newly_triggered:
        save_alerts(alerts_data)

    # Triggered banner
    just_triggered = [a for a in alerts_data.get('alerts', []) if a.get('triggered')]
    if just_triggered:
        banner_items = []
        for a in just_triggered:
            banner_items.append(html.Div([
                html.Strong(a['ticker']),
                html.Span(f" hit {'above' if a['type'] == 'ABOVE' else 'below'} ${a['target_price']:.2f}!"),
                dbc.Button("Dismiss", id={'type': 'alert-dismiss', 'id': a['id']},
                          size="sm", color="light", className="ms-2")
            ], style={"display": "inline-block", "marginRight": "20px"}))

        banner = dbc.Alert(banner_items, color="warning",
                          style={"marginBottom": "25px", "fontWeight": "500"})
    else:
        banner = html.Div()

    # Active alerts table
    active_alerts = [a for a in alerts_data.get('alerts', []) if not a.get('triggered')]
    if not active_alerts:
        active_content = html.P("No active alerts.", style={"color": "#888"})
    else:
        rows = []
        for alert in active_alerts:
            try:
                data = get_stock_quick_data(alert['ticker'])
                current_price = data['price'] if data else 'N/A'
                current_str = f"${current_price:.2f}" if isinstance(current_price, float) else current_price
            except:
                current_str = "N/A"

            rows.append(html.Tr([
                html.Td(alert['ticker'], style={"fontWeight": "600", "color": "#1a73e8"}),
                html.Td(f"{'Above' if alert['type'] == 'ABOVE' else 'Below'} ${alert['target_price']:.2f}"),
                html.Td(current_str),
                html.Td(alert['created_date']),
                html.Td(dbc.Button("Delete", id={'type': 'alert-delete', 'id': alert['id']},
                                  className="remove-btn", size="sm"))
            ]))

        active_content = html.Table([
            html.Thead(html.Tr([html.Th("Ticker"), html.Th("Condition"), html.Th("Current Price"),
                               html.Th("Created"), html.Th("")])),
            html.Tbody(rows)
        ], className="table table-hover", style={"width": "100%"})

    # Alert history (triggered)
    triggered_alerts = [a for a in alerts_data.get('alerts', []) if a.get('triggered')]
    if not triggered_alerts:
        history_content = html.P("No triggered alerts yet.", style={"color": "#888"})
    else:
        rows = []
        for alert in triggered_alerts:
            rows.append(html.Tr([
                html.Td(alert['ticker'], style={"fontWeight": "600", "color": "#1a73e8"}),
                html.Td(f"{'Above' if alert['type'] == 'ABOVE' else 'Below'} ${alert['target_price']:.2f}"),
                html.Td(alert.get('triggered_date', 'Unknown')),
            ]))

        history_content = html.Table([
            html.Thead(html.Tr([html.Th("Ticker"), html.Th("Condition"), html.Th("Triggered Date")])),
            html.Tbody(rows)
        ], className="table table-hover", style={"width": "100%"})

    return banner, active_content, history_content

# ============================================================================
# SETTINGS CALLBACKS
# ============================================================================

@app.callback(
    [Output('target-allocations-container', 'children'),
     Output('categories-container', 'children')],
    [Input('target-add-btn', 'n_clicks'),
     Input('save-settings-btn', 'n_clicks'),
     Input('category-add-btn', 'n_clicks'),
     Input({'type': 'target-delete', 'ticker': ALL}, 'n_clicks'),
     Input({'type': 'category-delete', 'name': ALL}, 'n_clicks')],
    [State('target-ticker', 'value'),
     State('target-pct', 'value'),
     State('rebalance-threshold', 'value'),
     State('new-category', 'value')],
    prevent_initial_call=False
)
def manage_settings(add_target_clicks, save_clicks, add_cat_clicks,
                   delete_target_clicks, delete_cat_clicks,
                   target_ticker, target_pct, threshold, new_category):
    """Manage settings"""
    ctx = callback_context
    settings = load_settings()
    expenses_data = load_expenses()

    # Handle add target allocation
    if ctx.triggered and 'target-add-btn' in ctx.triggered[0]['prop_id']:
        if target_ticker and target_pct:
            settings['target_allocations'][target_ticker.upper().strip()] = float(target_pct)
            save_settings(settings)

    # Handle save settings
    if ctx.triggered and 'save-settings-btn' in ctx.triggered[0]['prop_id']:
        if threshold:
            settings['rebalance_threshold'] = float(threshold)
            save_settings(settings)

    # Handle delete target
    if ctx.triggered and 'target-delete' in ctx.triggered[0]['prop_id']:
        import ast
        trigger_dict = ast.literal_eval(ctx.triggered[0]['prop_id'].split('.')[0])
        ticker_to_remove = trigger_dict['ticker']
        if ticker_to_remove in settings['target_allocations']:
            del settings['target_allocations'][ticker_to_remove]
            save_settings(settings)

    # Handle add category
    if ctx.triggered and 'category-add-btn' in ctx.triggered[0]['prop_id']:
        if new_category and new_category.strip() not in expenses_data.get('categories', []):
            expenses_data['categories'].append(new_category.strip())
            save_expenses(expenses_data)

    # Handle delete category
    if ctx.triggered and 'category-delete' in ctx.triggered[0]['prop_id']:
        import ast
        trigger_dict = ast.literal_eval(ctx.triggered[0]['prop_id'].split('.')[0])
        cat_to_remove = trigger_dict['name']
        if cat_to_remove in expenses_data.get('categories', []):
            expenses_data['categories'].remove(cat_to_remove)
            save_expenses(expenses_data)

    # Target allocations display
    targets = settings.get('target_allocations', {})
    if not targets:
        targets_content = html.P("No target allocations set.", style={"color": "#888"})
    else:
        total_pct = sum(targets.values())
        rows = []
        for ticker, pct in targets.items():
            rows.append(html.Div([
                html.Span(ticker, style={"fontWeight": "600", "color": "#1a73e8", "width": "80px", "display": "inline-block"}),
                html.Span(f"{pct}%", style={"width": "60px", "display": "inline-block"}),
                dbc.Button("X", id={'type': 'target-delete', 'ticker': ticker},
                          className="remove-btn", size="sm")
            ], style={"padding": "8px 0", "borderBottom": "1px solid #e3f2fd"}))

        rows.append(html.Div([
            html.Span("Total: ", style={"fontWeight": "600", "width": "80px", "display": "inline-block"}),
            html.Span(f"{total_pct}%", style={"fontWeight": "700",
                     "color": "#2e7d32" if total_pct == 100 else "#dc3545"})
        ], style={"padding": "12px 0", "borderTop": "2px solid #e3f2fd", "marginTop": "10px"}))

        targets_content = html.Div(rows)

    # Categories display
    categories = expenses_data.get('categories', [])
    if not categories:
        cats_content = html.P("No categories.", style={"color": "#888"})
    else:
        cat_rows = []
        for cat in categories:
            cat_rows.append(html.Div([
                html.Span(cat, style={"width": "150px", "display": "inline-block"}),
                dbc.Button("X", id={'type': 'category-delete', 'name': cat},
                          className="remove-btn", size="sm")
            ], style={"padding": "8px 0", "borderBottom": "1px solid #e3f2fd"}))
        cats_content = html.Div(cat_rows)

    return targets_content, cats_content

# ============================================================================
# PORTFOLIO PAGE CALLBACKS
# ============================================================================

@app.callback(
    [Output('portfolio-page-graph', 'figure'),
     Output('portfolio-page-summary', 'children'),
     Output('portfolio-page-holdings-table', 'children'),
     Output('portfolio-page-filter-ticker', 'options'),
     Output('portfolio-page-filter-ticker', 'value')],
    [Input('portfolio-page-filter-account', 'value'),
     Input('portfolio-page-filter-ticker', 'value'),
     Input('port-time-1d', 'n_clicks'),
     Input('port-time-1w', 'n_clicks'),
     Input('port-time-1m', 'n_clicks'),
     Input('port-time-3m', 'n_clicks'),
     Input('port-time-6m', 'n_clicks'),
     Input('port-time-1y', 'n_clicks'),
     Input('port-time-all', 'n_clicks'),
     Input('url', 'pathname')],
    prevent_initial_call=False
)
def update_portfolio_page(filter_account, filter_ticker, t1d, t1w, t1m, t3m, t6m, t1y, tall, pathname):
    """Update portfolio page with filters"""
    if pathname != '/portfolio':
        empty_fig = go.Figure()
        return empty_fig, html.Div(), html.Div(), [], "ALL"

    ctx = callback_context
    portfolio = load_portfolio()
    accounts = portfolio.get("accounts", [])

    # Determine time period
    time_period = "1M"  # default
    if ctx.triggered:
        trigger = ctx.triggered[0]['prop_id']
        if 'port-time-1d' in trigger:
            time_period = "1D"
        elif 'port-time-1w' in trigger:
            time_period = "1W"
        elif 'port-time-1m' in trigger:
            time_period = "1M"
        elif 'port-time-3m' in trigger:
            time_period = "3M"
        elif 'port-time-6m' in trigger:
            time_period = "6M"
        elif 'port-time-1y' in trigger:
            time_period = "1Y"
        elif 'port-time-all' in trigger:
            time_period = "All"

    # Build ticker options based on selected account (not all accounts)
    if filter_account and filter_account != 'ALL':
        # Only show tickers from the selected account
        account_tickers = set()
        for acc in accounts:
            if acc['id'] == filter_account:
                for h in acc.get("holdings", []):
                    account_tickers.add(h["ticker"])
        ticker_options = [{"label": "All Tickers", "value": "ALL"}] + \
                         [{"label": t, "value": t} for t in sorted(account_tickers)]
    else:
        # Show all tickers from all accounts
        all_tickers = set()
        for acc in accounts:
            for h in acc.get("holdings", []):
                all_tickers.add(h["ticker"])
        ticker_options = [{"label": "All Tickers", "value": "ALL"}] + \
                         [{"label": t, "value": t} for t in sorted(all_tickers)]

    # Reset ticker filter to ALL when account changes
    ticker_value = filter_ticker
    if ctx.triggered and 'portfolio-page-filter-account' in ctx.triggered[0]['prop_id']:
        ticker_value = "ALL"
    # Also reset if the current ticker isn't in the new options
    valid_tickers = [opt['value'] for opt in ticker_options]
    if ticker_value not in valid_tickers:
        ticker_value = "ALL"

    # Apply account filter
    filtered_accounts = accounts
    if filter_account and filter_account != 'ALL':
        filtered_accounts = [acc for acc in accounts if acc['id'] == filter_account]

    # Calculate values and build holdings list
    holdings_list = []
    total_value = 0
    total_cost = 0

    for account in filtered_accounts:
        for holding in account.get("holdings", []):
            # Apply ticker filter (use ticker_value which may have been reset)
            if ticker_value and ticker_value != 'ALL' and holding["ticker"] != ticker_value:
                continue

            data = get_stock_quick_data(holding["ticker"])
            if data:
                current_val = data["price"] * holding["shares"]
                cost_basis = holding["avg_cost"] * holding["shares"]
                gain = current_val - cost_basis
                gain_pct = (gain / cost_basis * 100) if cost_basis > 0 else 0

                holdings_list.append({
                    'account': account['name'],
                    'account_id': account['id'],
                    'ticker': holding["ticker"],
                    'shares': holding["shares"],
                    'avg_cost': holding["avg_cost"],
                    'price': data["price"],
                    'value': current_val,
                    'cost': cost_basis,
                    'gain': gain,
                    'gain_pct': gain_pct,
                    'change_1d': data.get('change_1d', 0),
                    'change_1m': data.get('change_1m', 0)
                })
                total_value += current_val
                total_cost += cost_basis

    # Create graph
    graph_fig = create_portfolio_trend_graph(time_period)
    graph_fig.update_layout(height=320, margin=dict(l=40, r=40, t=20, b=40))

    # Summary stats
    total_gain = total_value - total_cost
    total_pct = (total_gain / total_cost * 100) if total_cost > 0 else 0
    gain_class = "positive" if total_gain >= 0 else "negative"

    summary = dbc.Row([
        dbc.Col([
            html.Div([
                html.Span("Total Value: ", style={"color": "#666"}),
                html.Span(f"${total_value:,.2f}", style={"fontWeight": "700", "fontSize": "1.1rem"})
            ])
        ], width=3),
        dbc.Col([
            html.Div([
                html.Span("Cost Basis: ", style={"color": "#666"}),
                html.Span(f"${total_cost:,.2f}", style={"fontWeight": "600"})
            ])
        ], width=3),
        dbc.Col([
            html.Div([
                html.Span("Gain/Loss: ", style={"color": "#666"}),
                html.Span(f"{'+'if total_gain>=0 else ''}{total_gain:,.2f} ({total_pct:+.1f}%)",
                         className=gain_class, style={"fontWeight": "700"})
            ])
        ], width=3),
        dbc.Col([
            html.Div([
                html.Span("Positions: ", style={"color": "#666"}),
                html.Span(f"{len(holdings_list)}", style={"fontWeight": "600"})
            ])
        ], width=3),
    ], style={"padding": "15px", "backgroundColor": "#f8fbff", "borderRadius": "10px"})

    # Holdings table
    if not holdings_list:
        holdings_table = html.P("No holdings found.", style={"color": "#888"})
    else:
        rows = []
        for h in sorted(holdings_list, key=lambda x: x['value'], reverse=True):
            gain_class = "positive" if h['gain'] >= 0 else "negative"
            day_class = "positive" if h['change_1d'] >= 0 else "negative"

            rows.append(html.Tr([
                html.Td(h['account'], style={"fontSize": "0.85rem"}),
                html.Td(h['ticker'], style={"fontWeight": "600", "color": "#1a73e8"}),
                html.Td(f"{h['shares']:.2f}"),
                html.Td(f"${h['avg_cost']:.2f}"),
                html.Td(f"${h['price']:.2f}"),
                html.Td(f"${h['value']:,.2f}", style={"fontWeight": "500"}),
                html.Td(html.Span(f"{'+'if h['gain']>=0 else ''}{h['gain']:,.2f}",
                                 className=gain_class), style={"fontWeight": "500"}),
                html.Td(html.Span(f"{h['gain_pct']:+.1f}%", className=gain_class)),
                html.Td(html.Span(f"{h['change_1d']:+.2f}%", className=day_class)),
                html.Td(dbc.Button("X", id={'type': 'portfolio-holding-delete', 'account': h['account_id'], 'ticker': h['ticker']},
                                  color="danger", size="sm", outline=True,
                                  style={"padding": "2px 8px", "fontSize": "0.75rem"}))
            ]))

        holdings_table = html.Table([
            html.Thead(html.Tr([
                html.Th("Account"), html.Th("Ticker"), html.Th("Shares"),
                html.Th("Avg Cost"), html.Th("Price"), html.Th("Value"),
                html.Th("Gain $"), html.Th("Gain %"), html.Th("1D Change"), html.Th("")
            ], style={"fontSize": "0.85rem", "color": "#666"})),
            html.Tbody(rows)
        ], className="table table-hover", style={"width": "100%", "fontSize": "0.9rem"})

    return graph_fig, summary, holdings_table, ticker_options, ticker_value

# ============================================================================
# PORTFOLIO HOLDING DELETE CALLBACK
# ============================================================================

@app.callback(
    Output('url', 'pathname', allow_duplicate=True),
    Input({'type': 'portfolio-holding-delete', 'account': ALL, 'ticker': ALL}, 'n_clicks'),
    prevent_initial_call=True
)
def delete_portfolio_holding(n_clicks_list):
    """Delete a holding from portfolio (instant delete)"""
    ctx = callback_context
    if not ctx.triggered or not any(n_clicks_list):
        raise PreventUpdate

    # Get the button that was clicked
    triggered = ctx.triggered[0]
    if triggered['value'] is None:
        raise PreventUpdate

    # Parse the button ID to get account and ticker
    button_id = triggered['prop_id'].replace('.n_clicks', '')
    try:
        id_dict = json.loads(button_id)
        account_id = id_dict['account']
        ticker = id_dict['ticker']
    except:
        raise PreventUpdate

    # Load portfolio and remove the holding
    portfolio = load_portfolio()
    for account in portfolio.get('accounts', []):
        if account['id'] == account_id:
            account['holdings'] = [h for h in account['holdings'] if h['ticker'] != ticker]
            break

    save_portfolio(portfolio)

    # Return same pathname to refresh
    return '/portfolio'

# ============================================================================
# RUN APP
# ============================================================================

if __name__ == "__main__":
    app.run(debug=True, port=8050)

"""
Database operations using Supabase for cloud persistence.
Provides the same interface as the JSON file operations.
"""
import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Default user ID (can be extended for multi-user support later)
DEFAULT_USER_ID = "default"

# Initialize Supabase client (only if credentials are available)
supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def is_database_available():
    """Check if Supabase is configured and available"""
    return supabase is not None

# ============================================================================
# GENERIC DATABASE OPERATIONS
# ============================================================================

def _load_data(table_name: str, default_data: dict) -> dict:
    """Generic load function for any table"""
    if not is_database_available():
        return default_data

    try:
        response = supabase.table(table_name).select("data").eq("user_id", DEFAULT_USER_ID).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]["data"]
        return default_data
    except Exception as e:
        print(f"Error loading from {table_name}: {e}")
        return default_data

def _save_data(table_name: str, data: dict) -> bool:
    """Generic save function for any table (upsert)"""
    if not is_database_available():
        return False

    try:
        # Use upsert to insert or update
        supabase.table(table_name).upsert({
            "user_id": DEFAULT_USER_ID,
            "data": data
        }, on_conflict="user_id").execute()
        return True
    except Exception as e:
        print(f"Error saving to {table_name}: {e}")
        return False

# ============================================================================
# WATCHLIST OPERATIONS
# ============================================================================

def load_watchlist() -> dict:
    """Load watchlist from database"""
    return _load_data("watchlist", {"tickers": []})

def save_watchlist(data: dict) -> bool:
    """Save watchlist to database"""
    return _save_data("watchlist", data)

# ============================================================================
# PORTFOLIO OPERATIONS
# ============================================================================

def load_portfolio() -> dict:
    """Load portfolio from database"""
    return _load_data("portfolios", {"accounts": []})

def save_portfolio(data: dict) -> bool:
    """Save portfolio to database"""
    return _save_data("portfolios", data)

# ============================================================================
# PORTFOLIO HISTORY OPERATIONS
# ============================================================================

def load_portfolio_history() -> dict:
    """Load portfolio history from database"""
    return _load_data("portfolio_history", {"snapshots": []})

def save_portfolio_history(data: dict) -> bool:
    """Save portfolio history to database"""
    return _save_data("portfolio_history", data)

# ============================================================================
# TRADES OPERATIONS
# ============================================================================

def load_trades() -> dict:
    """Load trades from database"""
    return _load_data("trades", {"trades": []})

def save_trades(data: dict) -> bool:
    """Save trades to database"""
    return _save_data("trades", data)

# ============================================================================
# INCOME OPERATIONS
# ============================================================================

def load_income() -> dict:
    """Load income from database"""
    default_data = {
        "income": [],
        "recurring": [],
        "rsus": []
    }
    data = _load_data("income", default_data)
    # Ensure new keys exist for backward compatibility
    if "recurring" not in data:
        data["recurring"] = []
    if "rsus" not in data:
        data["rsus"] = []
    return data

def save_income(data: dict) -> bool:
    """Save income to database"""
    return _save_data("income", data)

# ============================================================================
# EXPENSES OPERATIONS
# ============================================================================

DEFAULT_EXPENSE_CATEGORIES = ["Dining", "Shopping", "Gas", "Entertainment", "Bills", "Travel", "Subscriptions", "Other"]

def load_expenses() -> dict:
    """Load expenses from database"""
    default_data = {
        "expenses": [],
        "categories": DEFAULT_EXPENSE_CATEGORIES,
        "budgets": {}
    }
    data = _load_data("expenses", default_data)
    # Ensure budgets key exists for backward compatibility
    if "budgets" not in data:
        data["budgets"] = {}
    # Update categories if using old format
    if "Food" in data.get("categories", []):
        data["categories"] = DEFAULT_EXPENSE_CATEGORIES
    return data

def save_expenses(data: dict) -> bool:
    """Save expenses to database"""
    return _save_data("expenses", data)

# ============================================================================
# ALERTS OPERATIONS
# ============================================================================

def load_alerts() -> dict:
    """Load alerts from database"""
    return _load_data("alerts", {"alerts": []})

def save_alerts(data: dict) -> bool:
    """Save alerts to database"""
    return _save_data("alerts", data)

# ============================================================================
# SETTINGS OPERATIONS
# ============================================================================

def load_settings() -> dict:
    """Load settings from database"""
    return _load_data("settings", {"target_allocations": {}, "rebalance_threshold": 5})

def save_settings(data: dict) -> bool:
    """Save settings to database"""
    return _save_data("settings", data)

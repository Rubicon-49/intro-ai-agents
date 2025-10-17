"""
download_financial_data.py

Utility script for retrieving market and financial statement data for
a fixed portfolio of stocks. It downloads:
- daily closing prices for the last 5 years
- income statement, balance sheet, and cash flow data

All results are saved as JSON files under the 'data/' folder.

Dependencies:
    pip install yfinance pandas
"""

from pathlib import Path
import pandas as pd
import yfinance as yf
from typing import Optional

# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------
TICKERS = ["AAPL", "TSLA", "MSFT"]
DATA_DIR = Path(__file__).parent.parent / "data"

# -------------------------------------------------------------------
# Download historical prices
# -------------------------------------------------------------------
def download_prices(tickers: list[str], years: int = 5) -> pd.DataFrame:
    """
    Download end-of-day closing prices for the given tickers.
    
    Args:
        tickers (list[str]): Stock tickers to download.
        years (int): Number of years of daily history.
        
    Returns:
        pd.DataFrame: Daily closing prices.
    """
    print(f"Downloading {years} years of daily prices for: {', '.join(tickers)}")
    data: Optional[pd.DataFrame] = yf.download(tickers, period=f"{years}y", interval="1d")
    
    if data is None or "Close" not in data:
        raise ValueError("Failed to retrieve price data or missing 'Close' column.")
    
    data = data["Close"].reset_index()
    
    # Reset index for JSON serialization (so 'Date' is a column)
    data = data.reset_index()
    json_path = DATA_DIR / "stock_prices.json"
    data.to_json(json_path, orient="records", date_format="iso")
    
    print(f"Saved prices to {json_path}")
    return data

# -------------------------------------------------------------------
# Download company financial statements
# -------------------------------------------------------------------
def download_financials(ticker: str):
    """
    Download income statement, balance sheet, and cash flow for a ticker.
    
    Args:
        ticker (str): Stock symbol.
        
    Returns:
        dict[str, pd.DataFrame]: Dictionary with financial statement DataFrames.
    """
    print(f"Downloading financial statements for {ticker} ...")
    stock =yf.Ticker(ticker)
    
    financials = {
        "income_statement": stock.financials,
        "balance_sheet": stock.balance_sheet,
        "cash_flow": stock.cashflow,
    }
    
    for name, df in financials.items():
        # Convert DataFrame to JSON-friendly format
        df = df.fillna(0).T.reset_index().rename(columns={"index": "Period"})
        out_path = DATA_DIR / f"{ticker.lower()}_{name}.json"
        df.to_json(out_path, orient="records", date_format="iso")
        print(f"Saved {name} to {out_path}")
        
    return financials

# -------------------------------------------------------------------
# Main execution
# -------------------------------------------------------------------
if __name__ == "__main__":
    # Download 5 years of prices
    prices = download_prices(TICKERS, years=2)
    
    # Download financial statements for each ticker
    for t in TICKERS:
        download_financials(t)
        
    print("\n All data downloaded successfully as JSON.")
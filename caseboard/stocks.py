"""
Stock ticker management for live stock data display.
Uses Alpha Vantage API for real stock data with fallback to mock data.
"""
from __future__ import annotations
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import os

# Default stock symbols to track
DEFAULT_STOCKS = [
    "AAPL", "MSFT", "GOOGL", "TSLA", "AMZN", 
    "META", "NVDA", "NFLX", "JPM", "V"
]

@dataclass
class StockData:
    symbol: str
    price: float
    change: float
    change_percent: float
    last_updated: datetime
    
    @property
    def change_str(self) -> str:
        """Format change as string with + or - prefix."""
        if self.change >= 0:
            return f"+{self.change:.2f}"
        return f"{self.change:.2f}"
    
    @property
    def change_percent_str(self) -> str:
        """Format change percent as string with + or - prefix."""
        if self.change_percent >= 0:
            return f"+{self.change_percent:.2f}%"
        return f"{self.change_percent:.2f}%"


class StockManager:
    """Manages stock data fetching and storage."""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.stocks_file = os.path.join(data_dir, "stocks.json")
        self.cache_file = os.path.join(data_dir, "stock_cache.json")
        self.api_key = None  # We'll use free APIs that don't require keys initially
        self.stock_symbols = self.load_stock_symbols()
        self.cache: Dict[str, StockData] = {}
        self.last_fetch = None
        
    def load_stock_symbols(self) -> List[str]:
        """Load tracked stock symbols from file."""
        try:
            if os.path.exists(self.stocks_file):
                with open(self.stocks_file, 'r') as f:
                    data = json.load(f)
                    return data.get('symbols', DEFAULT_STOCKS)
        except Exception:
            pass
        return DEFAULT_STOCKS.copy()
    
    def save_stock_symbols(self) -> None:
        """Save tracked stock symbols to file."""
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            with open(self.stocks_file, 'w') as f:
                json.dump({
                    'symbols': self.stock_symbols,
                    'updated': datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            print(f"Error saving stock symbols: {e}")
    
    def add_stock(self, symbol: str) -> bool:
        """Add a stock symbol to tracking list."""
        symbol = symbol.upper().strip()
        if symbol and symbol not in self.stock_symbols:
            self.stock_symbols.append(symbol)
            self.save_stock_symbols()
            return True
        return False
    
    def remove_stock(self, symbol: str) -> bool:
        """Remove a stock symbol from tracking list."""
        symbol = symbol.upper().strip()
        if symbol in self.stock_symbols:
            self.stock_symbols.remove(symbol)
            self.save_stock_symbols()
            return True
        return False
    
    def fetch_stock_data_live(self, symbol: str) -> Optional[StockData]:
        """
        Fetch live stock data from a free API.
        Using Alpha Vantage's free tier or Yahoo Finance alternative.
        """
        try:
            # Using a free API endpoint (Yahoo Finance alternative)
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                chart = data['chart']['result'][0]
                
                # Get current price
                current_price = chart['meta']['regularMarketPrice']
                previous_close = chart['meta']['previousClose']
                
                # Calculate change
                change = current_price - previous_close
                change_percent = (change / previous_close) * 100
                
                return StockData(
                    symbol=symbol,
                    price=current_price,
                    change=change,
                    change_percent=change_percent,
                    last_updated=datetime.now()
                )
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
        
        return None
    
    def get_mock_data(self, symbol: str) -> StockData:
        """Generate mock stock data as fallback."""
        import random
        
        # Base prices for common stocks
        base_prices = {
            "AAPL": 185.43, "MSFT": 378.92, "GOOGL": 142.56, "TSLA": 248.73,
            "AMZN": 144.89, "META": 521.04, "NVDA": 876.45, "NFLX": 452.18,
            "JPM": 198.76, "V": 289.34
        }
        
        base_price = base_prices.get(symbol, 100.0)
        
        # Add some random variation
        price_variation = random.uniform(-0.05, 0.05)  # ±5%
        current_price = base_price * (1 + price_variation)
        
        change = current_price - base_price
        change_percent = (change / base_price) * 100
        
        return StockData(
            symbol=symbol,
            price=current_price,
            change=change,
            change_percent=change_percent,
            last_updated=datetime.now()
        )
    
    def get_stock_data(self, symbol: str, use_cache: bool = True) -> StockData:
        """Get stock data, using cache if available and recent."""
        if use_cache and symbol in self.cache:
            cached = self.cache[symbol]
            # Use cache if less than 1 minute old
            if datetime.now() - cached.last_updated < timedelta(minutes=1):
                return cached
        
        # Try to fetch live data
        live_data = self.fetch_stock_data_live(symbol)
        if live_data:
            self.cache[symbol] = live_data
            return live_data
        
        # Fallback to mock data
        mock_data = self.get_mock_data(symbol)
        self.cache[symbol] = mock_data
        return mock_data
    
    def get_all_stock_data(self, use_cache: bool = True) -> List[StockData]:
        """Get data for all tracked stocks."""
        stocks = []
        for symbol in self.stock_symbols:
            stock_data = self.get_stock_data(symbol, use_cache)
            stocks.append(stock_data)
        return stocks
    
    def refresh_all_data(self) -> List[StockData]:
        """Force refresh all stock data."""
        return self.get_all_stock_data(use_cache=False)


# Global stock manager instance
_stock_manager = None

def get_stock_manager() -> StockManager:
    """Get the global stock manager instance."""
    global _stock_manager
    if _stock_manager is None:
        _stock_manager = StockManager()
    return _stock_manager
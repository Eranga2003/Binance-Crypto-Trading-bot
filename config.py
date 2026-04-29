import os
from dotenv import load_dotenv

load_dotenv()

# Binance API Configuration
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "")
TESTNET = True # Set to False for live trading

# Strategy Parameters
RISK_PERCENT_PER_TRADE = 0.03
PORTFOLIO_ALLOCATION = 0.05
LEVERAGE = 5
TAKE_PROFIT_PERCENT = 0.03

# Market Hours (EST)
US_MARKET_OPEN_HOUR = 9
US_MARKET_OPEN_MINUTE = 30
US_MARKET_CLOSE_HOUR = 16
US_MARKET_CLOSE_MINUTE = 0

# Timeframes
TF_1H = '1h'
TF_15M = '15m'
# 25m is handled via 5m resampling since Binance doesn't support 25m natively.

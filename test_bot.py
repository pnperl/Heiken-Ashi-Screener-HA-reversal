"""
Unit tests for trading bot - verify all logic
Run: python -m pytest test_bot.py -v
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from zoneinfo import ZoneInfo

# Import bot components
# (In real scenario, import from bot_v2_optimized.py)


class TestHeikanAshi:
    """Test Heiken-Ashi calculation"""
    
    def test_ha_basic(self):
        """HA should smooth candles"""
        df = pd.DataFrame({
            'Open': [100, 101, 102, 103, 104] * 3,
            'High': [102, 103, 104, 105, 106] * 3,
            'Low': [99, 100, 101, 102, 103] * 3,
            'Close': [101, 102, 103, 104, 105] * 3,
        })
        
        ha = heikin_ashi(df)
        assert ha is not None
        assert len(ha) >= len(df) - 5
        assert 'open' in ha.columns
        assert 'close' in ha.columns
    
    def test_ha_insufficient_data(self):
        """HA should return None if < 10 rows"""
        df = pd.DataFrame({
            'Open': [100] * 5,
            'High': [102] * 5,
            'Low': [99] * 5,
            'Close': [101] * 5,
        })
        
        ha = heikin_ashi(df)
        assert ha is None


class TestIndicators:
    """Test indicator calculations"""
    
    def test_rsi_range(self):
        """RSI should be 0-100"""
        df = pd.DataFrame({
            'Open': np.random.randn(50) + 100,
            'High': np.random.randn(50) + 102,
            'Low': np.random.randn(50) + 99,
            'Close': np.random.randn(50) + 101,
            'Volume': np.random.randint(1000, 10000, 50),
        })
        
        indicators = compute_indicators(df)
        assert indicators is not None
        assert 0 <= indicators['rsi'] <= 100
    
    def test_atr_positive(self):
        """ATR should always be positive"""
        df = pd.DataFrame({
            'Open': [100] * 30,
            'High': [102] * 30,
            'Low': [99] * 30,
            'Close': [101] * 30,
            'Volume': [5000] * 30,
        })
        
        indicators = compute_indicators(df)
        assert indicators is not None
        assert indicators['atr'] > 0


class TestSignalDetection:
    """Test signal detection logic"""
    
    def test_bullish_reversal(self):
        """Should detect bullish pattern"""
        ha = pd.DataFrame({
            'open': [101, 100, 99],
            'close': [100, 99, 100],  # prev close < open, curr close > open
            'high': [102, 101, 101],
            'low': [99, 98, 98],
        })
        
        df = pd.DataFrame({
            'Close': [101, 102, 103],
            'High': [103, 104, 105],
            'Low': [100, 101, 102],
            'Volume': [5000, 6000, 7000],
        })
        
        indicators = {
            'rsi': 40,
            'atr': 1.0,
            'ema': 101,
            'volume': 7000,
            'volume_ma': 5000,
        }
        
        signal, conf = detect_signal(ha, df, indicators, detect_profile("BTC-USD"))
        assert conf > 0  # Should have some confidence
    
    def test_no_signal_insufficient_data(self):
        """Should return None if insufficient data"""
        ha = None
        df = pd.DataFrame()
        indicators = None
        
        signal, conf = detect_signal(ha, df, indicators, detect_profile("BTC-USD"))
        assert signal is None
        assert conf == 0.0


class TestAssetProfile:
    """Test asset profile detection"""
    
    def test_crypto_24_7(self):
        """Crypto should be 24/7"""
        profile = detect_profile("BTC-USD")
        assert profile.type == "CRYPTO"
        assert profile.tz == "UTC"
        assert profile.hours is None
    
    def test_india_nse_hours(self):
        """India should be 9:15-3:30 IST"""
        profile = detect_profile("RELIANCE.NS")
        assert profile.type == "INDIA"
        assert profile.tz == "Asia/Kolkata"
        assert profile.hours == ("09:15", "15:30")
    
    def test_us_market_hours(self):
        """US should be 9:30-4:00 EST"""
        profile = detect_profile("AAPL")
        assert profile.type == "US_STOCK"
        assert profile.tz == "America/New_York"
        assert profile.hours == ("09:30", "16:00")


class TestRateLimiter:
    """Test rate limiting"""
    
    def test_allows_requests_within_limit(self):
        """Should allow requests under limit"""
        limiter = RateLimiter(max_requests=5, window_seconds=10)
        
        for _ in range(5):
            assert limiter.can_request() is True
        
        assert limiter.can_request() is False
    
    def test_clears_old_requests(self):
        """Should clear requests outside window"""
        limiter = RateLimiter(max_requests=2, window_seconds=1)
        
        limiter.can_request()
        limiter.can_request()
        assert limiter.can_request() is False
        
        # Wait for window to expire
        import time
        time.sleep(1.1)
        
        # Should allow again
        assert limiter.can_request() is True


class TestPositionManagement:
    """Test position entry/exit logic"""
    
    def test_enter_position_call(self):
        """Should enter CALL position with proper SL/TP"""
        position = Position(
            symbol="BTC-USD",
            type=PositionType.CALL,
            entry_price=50000,
            entry_time=datetime.now(IST),
            entry_atr=500,
        )
        
        profile = detect_profile("BTC-USD")
        entered = enter_position("BTC-USD", position, profile, 0.65)
        
        assert entered is True
        assert position.quantity > 0
        assert position.trailing_sl < position.entry_price
        assert position.trailing_tp > position.entry_price
    
    def test_manage_position_trailing_sl(self):
        """Trailing SL should move up on winning trades"""
        position = Position(
            symbol="BTC-USD",
            type=PositionType.CALL,
            entry_price=50000,
            entry_time=datetime.now(IST),
            entry_atr=500,
            trailing_sl=49000,
            trailing_tp=51000,
        )
        
        indicators = {'atr': 600}
        profile = detect_profile("BTC-USD")
        
        # Price moves up
        is_open, reason = manage_position(position, 50500, indicators, profile)
        
        assert is_open is True
        assert position.trailing_sl > 49000  # SL should move up
        assert position.max_favorable_excursion > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
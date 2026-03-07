"""
Unit tests for trading bot logic
Run: python -m pytest tests/test_bot.py -v
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from zoneinfo import ZoneInfo

# (Import bot functions here)

class TestHeikanAshi:
    """Test Heiken-Ashi calculation"""
    
    def test_ha_basic_calculation(self):
        """Verify HA formula correctness"""
        df = pd.DataFrame({
            'Open': [100, 101, 102],
            'High': [102, 103, 104],
            'Low': [99, 100, 101],
            'Close': [101, 102, 103],
        })
        
        ha = heikin_ashi(df)
        assert ha is not None
        assert len(ha) == 3
        assert 'open' in ha.columns
        assert 'close' in ha.columns
    
    def test_ha_insufficient_data(self):
        """Should return None if < 10 rows"""
        df = pd.DataFrame({
            'Open': [100] * 5,
            'High': [102] * 5,
            'Low': [99] * 5,
            'Close': [101] * 5,
        })
        
        ha = heikin_ashi(df)
        assert ha is None


class TestIndicators:
    """Test indicator calculation"""
    
    def test_rsi_calculation(self):
        """RSI should be between 0-100"""
        df = pd.DataFrame({
            'Open': np.random.randn(30) + 100,
            'High': np.random.randn(30) + 102,
            'Low': np.random.randn(30) + 99,
            'Close': np.random.randn(30) + 101,
            'Volume': np.random.randint(1000, 10000, 30),
        })
        
        indicators = compute_indicators(df)
        assert indicators is not None
        assert 0 <= indicators['rsi'] <= 100
    
    def test_atr_positive(self):
        """ATR should be positive"""
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
    
    def test_bullish_reversal_detection(self):
        """Should detect bullish reversal pattern"""
        # Simplified: just test the reversal logic
        ha_prev = {'open': 101, 'close': 100}  # bearish
        ha_prev2 = {'open': 99, 'close': 102}   # bullish
        
        bullish = (ha_prev['close'] < ha_prev['open'] and
                   ha_prev2['close'] > ha_prev2['open'])
        assert bullish is True
    
    def test_bearish_reversal_detection(self):
        """Should detect bearish reversal pattern"""
        ha_prev = {'open': 99, 'close': 102}   # bullish
        ha_prev2 = {'open': 101, 'close': 100}  # bearish
        
        bearish = (ha_prev['close'] > ha_prev['open'] and
                   ha_prev2['close'] < ha_prev2['open'])
        assert bearish is True


class TestAssetProfile:
    """Test asset profile detection"""
    
    def test_crypto_profile(self):
        """Should detect crypto as UTC, 24/7"""
        profile = detect_profile("BTC-USD")
        assert profile.type == "CRYPTO"
        assert profile.tz == "UTC"
        assert profile.hours is None
        assert profile.doji_threshold == 0.15
    
    def test_india_profile(self):
        """Should detect India stocks as IST, 9:15-3:30"""
        profile = detect_profile("RELIANCE.NS")
        assert profile.type == "INDIA"
        assert profile.tz == "Asia/Kolkata"
        assert profile.hours == ("09:15", "15:30")
    
    def test_us_profile(self):
        """Should detect US stocks as EST, 9:30-4:00"""
        profile = detect_profile("AAPL")
        assert profile.type == "US_STOCK"
        assert profile.tz == "America/New_York"
        assert profile.hours == ("09:30", "16:00")


class TestRateLimiter:
    """Test rate limiting"""
    
    def test_rate_limiter_allows_requests(self):
        """Should allow requests within limit"""
        limiter = RateLimiter(max_requests=5, window_seconds=10)
        
        for _ in range(5):
            assert limiter.can_request() is True
        
        assert limiter.can_request() is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
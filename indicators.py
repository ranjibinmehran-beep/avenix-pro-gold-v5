import pandas as pd
import numpy as np

def calculate_rsi(df, period=14):
    if len(df) < period + 1:
        df['RSI'] = 50.0
        return df
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).copy()
    loss = (-delta.where(delta < 0, 0)).copy()
    avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
    rs = avg_gain / (avg_loss + 1e-10)
    df['RSI'] = 100 - (100 / (1 + rs))
    df['RSI'] = df['RSI'].fillna(50.0)
    return df

def calculate_ichimoku(df, n1=9, n2=26, n3=52):
    if len(df) < n3:
        df['tenkan_sen'] = df['close']
        df['kijun_sen'] = df['close']
        df['senkou_span_a'] = df['close']
        df['senkou_span_b'] = df['close']
        df['chikou_span'] = df['close']
        return df
    period9_high = df['high'].rolling(window=n1).max()
    period9_low = df['low'].rolling(window=n1).min()
    df['tenkan_sen'] = (period9_high + period9_low) / 2
    period26_high = df['high'].rolling(window=n2).max()
    period26_low = df['low'].rolling(window=n2).min()
    df['kijun_sen'] = (period26_high + period26_low) / 2
    df['senkou_span_a'] = ((df['tenkan_sen'] + df['kijun_sen']) / 2).shift(n2)
    period52_high = df['high'].rolling(window=n3).max()
    period52_low = df['low'].rolling(window=n3).min()
    df['senkou_span_b'] = ((period52_high + period52_low) / 2).shift(n2)
    df['chikou_span'] = df['close'].shift(-n2)
    return df

def calculate_moving_averages(df, ma_short=20, ma_medium=50, ma_long=200):
    df[f'EMA_{ma_short}'] = df['close'].ewm(span=ma_short, adjust=False).mean()
    df[f'EMA_{ma_medium}'] = df['close'].ewm(span=ma_medium, adjust=False).mean()
    df[f'EMA_{ma_long}'] = df['close'].ewm(span=ma_long, adjust=False).mean()
    return df

def calculate_macd(df, fast=12, slow=26, signal=9):
    """
    Calculates the MACD line, Signal line, and MACD Histogram.
    """
    if len(df) < slow:
        df['macd_line'] = 0.0
        df['macd_signal'] = 0.0
        df['macd_hist'] = 0.0
        return df
    ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
    ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
    df['macd_line'] = ema_fast - ema_slow
    df['macd_signal'] = df['macd_line'].ewm(span=signal, adjust=False).mean()
    df['macd_hist'] = df['macd_line'] - df['macd_signal']
    return df

def calculate_bollinger_bands(df, period=20, std_dev=2.0):
    """
    Calculates Bollinger Bands: Middle, Upper, and Lower.
    """
    if len(df) < period:
        df['bb_middle'] = df['close']
        df['bb_upper'] = df['close']
        df['bb_lower'] = df['close']
        return df
    df['bb_middle'] = df['close'].rolling(window=period).mean()
    rolling_std = df['close'].rolling(window=period).std()
    df['bb_upper'] = df['bb_middle'] + (rolling_std * std_dev)
    df['bb_lower'] = df['bb_middle'] - (rolling_std * std_dev)
    return df

def process_all_indicators(df, config):
    df = calculate_rsi(df, period=config.get("rsi_period", 14))
    df = calculate_ichimoku(df, 
                            n1=config.get("ichimoku_tenkan", 9), 
                            n2=config.get("ichimoku_kijun", 26), 
                            n3=config.get("ichimoku_senkou_b", 52))
    df = calculate_moving_averages(df, 
                                   ma_short=config.get("ma_short", 20), 
                                   ma_medium=config.get("ma_medium", 50), 
                                   ma_long=config.get("ma_long", 200))
    df = calculate_macd(df, 
                        fast=config.get("macd_fast", 12), 
                        slow=config.get("macd_slow", 26), 
                        signal=config.get("macd_signal", 9))
    df = calculate_bollinger_bands(df, 
                                   period=config.get("bb_period", 20), 
                                   std_dev=config.get("bb_std_dev", 2.0))
    return df

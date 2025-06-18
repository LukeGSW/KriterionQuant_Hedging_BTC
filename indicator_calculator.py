# File: indicator_calculator.py
# Modulo per il progetto KriterionQuant Hedging App

import pandas as pd
import numpy as np

class IndicatorCalculator:
    """
    Contiene una collezione di metodi statici per calcolare vari
    indicatori tecnici su un DataFrame di dati di mercato.
    """
    @staticmethod
    def add_moving_average(df: pd.DataFrame, period: int, price_col: str = 'adj_close') -> pd.DataFrame:
        """Aggiunge una colonna per la media mobile semplice (SMA)."""
        df[f'sma_{period}'] = df[price_col].rolling(window=period).mean()
        return df

    @staticmethod
    def add_rsi(df: pd.DataFrame, period: int = 14, price_col: str = 'adj_close') -> pd.DataFrame:
        """Aggiunge una colonna per il Relative Strength Index (RSI)."""
        delta = df[price_col].diff()
        gain = delta.where(delta > 0, 0).ewm(com=period - 1, min_periods=period).mean()
        loss = -delta.where(delta < 0, 0).ewm(com=period - 1, min_periods=period).mean()
        
        rs = gain / loss
        df[f'rsi_{period}'] = 100 - (100 / (1 + rs))
        return df

    @staticmethod
    def add_bollinger_bands(df: pd.DataFrame, period: int = 20, std: float = 2.0, price_col: str = 'adj_close') -> pd.DataFrame:
        """Aggiunge le Bande di Bollinger al DataFrame."""
        sma = df[price_col].rolling(window=period).mean()
        rolling_std = df[price_col].rolling(window=period).std()
        
        df[f'BBM_{period}_{std}'] = sma
        df[f'BBU_{period}_{std}'] = sma + (rolling_std * std)
        df[f'BBL_{period}_{std}'] = sma - (rolling_std * std)
        return df

    @staticmethod
    def add_adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """Aggiunge l'Average Directional Index (ADX) al DataFrame."""
        high = df['high']
        low = df['low']
        close = df['close']
        
        plus_dm = high.diff()
        minus_dm = low.diff()
        
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm > 0] = 0
        
        tr1 = pd.DataFrame(high - low)
        tr2 = pd.DataFrame(abs(high - close.shift(1)))
        tr3 = pd.DataFrame(abs(low - close.shift(1)))
        
        tr = pd.concat([tr1, tr2, tr3], axis=1, sort=False).max(axis=1)
        
        # Usiamo una media mobile esponenziale per lo smoothing come da prassi
        atr = tr.ewm(alpha=1/period, min_periods=period).mean()
        
        plus_di = 100 * (plus_dm.ewm(alpha=1/period, min_periods=period).mean() / atr)
        minus_di = 100 * (abs(minus_dm.ewm(alpha=1/period, min_periods=period).mean()) / atr)
        
        dx = (abs(plus_di - minus_di) / abs(plus_di + minus_di)) * 100
        adx = dx.ewm(alpha=1/period, min_periods=period).mean()
        
        df[f'ADX_{period}'] = adx
        return df

# File: backtester.py
# Modulo per il progetto KriterionQuant Hedging App

import pandas as pd
import numpy as np

class VectorizedBacktester:
    """
    Contiene la logica di backtesting vettoriale.
    Simula una strategia "always-long" su un asset e una strategia di hedging.
    """
    def run_backtest(self, data: pd.DataFrame, strategy_signal: pd.Series, 
                     initial_capital: float, hedge_ratio: float) -> dict:
        """
        Esegue il backtest e restituisce un dizionario con le equity lines e i rendimenti.

        Args:
            data (pd.DataFrame): DataFrame con dati OHLC.
            strategy_signal (pd.Series): Serie con segnale di hedging (-1 per short, 0 per no hedge).
            initial_capital (float): Capitale iniziale.
            hedge_ratio (float): Frazione del capitale da coprire (es. 0.5 per 50%).

        Returns:
            dict: Dizionario contenente le curve di equity e i rendimenti della componente short.
        """
        # Calcolo dei rendimenti giornalieri dell'asset
        returns = data['adj_close'].pct_change()

        # --- Calcolo rendimenti della sola componente short ---
        # Questo calcola il rendimento delle sole operazioni di hedging (short o flat)
        hedge_only_returns = returns * strategy_signal.shift(1) * -1
        
        # --- Strategia 1: Buy and Hold (Long Only) ---
        long_only_equity = (1 + returns).cumprod() * initial_capital
        long_only_equity.iloc[0] = initial_capital

        # --- Strategia 2: Hedged (Strategia Completa) ---
        # Posizione della parte coperta: 0 se in hedge (flat), 1 se non in hedge (long)
        hedged_part_position = np.where(strategy_signal.shift(1) == -1, 0, 1)
        
        # Rendimento della parte non coperta (sempre long)
        unhedged_part_returns = returns * (1 - hedge_ratio)
        
        # Rendimento della parte coperta (che è long o flat)
        hedged_part_returns = returns * hedged_part_position * hedge_ratio

        # Rendimento totale della strategia coperta
        hedged_strategy_returns = unhedged_part_returns + hedged_part_returns
        
        hedged_equity = (1 + hedged_strategy_returns).cumprod() * initial_capital
        hedged_equity.iloc[0] = initial_capital

        # Restituisce un dizionario con tutti i risultati
        results = {
            'long_only': long_only_equity.dropna(),
            'hedged': hedged_equity.dropna(),
            'hedge_only_returns': hedge_only_returns.dropna(),
            'signal': strategy_signal
        }
        return results

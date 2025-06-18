# File: performance_analyzer.py
# Modulo per il progetto KriterionQuant Hedging App

import pandas as pd
import numpy as np

class PerformanceAnalyzer:
    """
    Calcola un set completo di metriche di performance (KPI) a partire 
    dai risultati di un backtest.
    """
    def __init__(self, equity_series: pd.Series, positions: pd.Series, hedge_only_returns: pd.Series = None):
        """
        Inizializza l'analizzatore con le serie di dati necessarie.

        Args:
            equity_series (pd.Series): La curva di equity del portafoglio.
            positions (pd.Series): La serie di posizioni prese nel tempo.
            hedge_only_returns (pd.Series, optional): I rendimenti della sola componente short.
        """
        self.equity = equity_series.dropna()
        self.returns = self.equity.pct_change().fillna(0)
        self.positions = positions
        self.initial_capital = self.equity.iloc[0] if not self.equity.empty else 0
        self.hedge_only_returns = hedge_only_returns

    def calculate_kpis(self) -> dict:
        """
        Calcola e restituisce un dizionario con tutti i KPI.
        """
        if len(self.equity) < 2:
            return {
                'Net Profit': 0, 'Profit Factor': 0, 'Sharpe Ratio': 0,
                'Max Drawdown': 0, 'Return on MaxDD': 0, 'Num Trades': 0,
                'Short-Only MaxDD': 0
            }

        # Calcolo Net Profit
        net_profit = self.equity.iloc[-1] - self.initial_capital

        # Calcolo Profit Factor
        gross_profits = self.returns[self.returns > 0].sum()
        gross_losses = self.returns[self.returns < 0].sum()
        profit_factor = gross_profits / abs(gross_losses) if gross_losses != 0 else np.inf

        # Calcolo Sharpe Ratio (annualizzato)
        sharpe_ratio = (self.returns.mean() / self.returns.std()) * np.sqrt(252) if self.returns.std() != 0 else 0

        # Calcolo Max Drawdown del portafoglio
        running_max = self.equity.cummax()
        drawdown = (self.equity - running_max) / running_max
        max_drawdown = drawdown.min()

        # Calcolo Return on Max Drawdown (Calmar Ratio)
        cumulative_return = (self.equity.iloc[-1] / self.initial_capital) - 1
        num_years = len(self.equity) / 252
        annualized_return = ((1 + cumulative_return) ** (1 / num_years)) - 1 if num_years > 0 else 0
        return_on_max_dd = annualized_return / abs(max_drawdown) if max_drawdown != 0 else np.inf

        # Calcolo Numero di Trades
        num_trades = (self.positions.diff().abs() != 0).sum()

        kpis = {
            "Net Profit": net_profit,
            "Profit Factor": profit_factor,
            "Sharpe Ratio": sharpe_ratio,
            "Max Drawdown": max_drawdown,
            "Return on MaxDD": return_on_max_dd,
            "Num Trades": num_trades
        }

        # Calcolo del Max Drawdown per la sola componente short, se disponibile
        if self.hedge_only_returns is not None:
            hedge_equity = (1 + self.hedge_only_returns.fillna(0)).cumprod() * self.initial_capital
            hedge_running_max = hedge_equity.cummax()
            hedge_drawdown = (hedge_equity - hedge_running_max) / hedge_running_max
            kpis['Short-Only MaxDD'] = hedge_drawdown.min()
        else:
            kpis['Short-Only MaxDD'] = 0.0
            
        return kpis

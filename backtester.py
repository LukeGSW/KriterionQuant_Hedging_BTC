# File: backtester.py (Versione 2.0 - Event-Driven)
# Modulo per il progetto KriterionQuant Hedging App

import pandas as pd
import numpy as np

class EventDrivenBacktester:
    """
    Esegue un backtest basato su un ciclo (event-driven) che permette
    l'implementazione di logiche complesse come lo stop loss.
    """
    def run_backtest(self, data: pd.DataFrame, strategy_signal: pd.Series, 
                     initial_capital: float, hedge_ratio: float, 
                     stop_loss_perc: float) -> dict:
        """
        Esegue il backtest e restituisce i risultati.

        Args:
            data (pd.DataFrame): Dati OHLC e indicatori.
            strategy_signal (pd.Series): Segnali di entrata (-1 per iniziare hedge).
            initial_capital (float): Capitale iniziale.
            hedge_ratio (float): Frazione del capitale da coprire.
            stop_loss_perc (float): Percentuale di stop loss (es. 0.10 per 10%).

        Returns:
            dict: Dizionario con curve di equity e altri risultati.
        """
        positions = pd.Series(index=data.index, dtype=float).fillna(0)
        
        # Stato del backtest
        is_hedged = False
        entry_price = 0.0

        # Ciclo principale del backtest
        for i in range(1, len(data)):
            # Se siamo coperti, verifichiamo le condizioni di uscita
            if is_hedged:
                # Condizione di uscita 1: Stop Loss
                stop_loss_triggered = data['close'][i-1] >= entry_price * (1 + stop_loss_perc)
                # Condizione di uscita 2: Il segnale base scompare
                signal_exited = strategy_signal[i-1] == 0

                if stop_loss_triggered or signal_exited:
                    is_hedged = False
                    entry_price = 0.0
            
            # Se NON siamo coperti, verifichiamo la condizione di entrata
            else:
                if strategy_signal[i-1] == -1:
                    is_hedged = True
                    # L'entrata avviene all'apertura del giorno corrente
                    entry_price = data['open'][i]
            
            # Registriamo la posizione per il giorno corrente: 0 se coperti, 1 se long
            if is_hedged:
                positions[i] = 0
            else:
                positions[i] = 1

        # --- Calcolo finanziario vettorizzato basato sulle posizioni finali ---
        returns = data['adj_close'].pct_change().fillna(0)

        # Rendimento della parte non coperta (sempre long)
        unhedged_part_returns = returns * (1 - hedge_ratio)
        
        # Rendimento della parte coperta (long o flat, in base alle posizioni finali)
        hedged_part_returns = returns * positions.shift(1) * hedge_ratio
        
        # Rendimento totale
        hedged_strategy_returns = unhedged_part_returns + hedged_part_returns
        
        # Calcolo curve di equity
        long_only_equity = (1 + returns).cumprod() * initial_capital
        hedged_equity = (1 + hedged_strategy_returns).cumprod() * initial_capital
        
        # Calcolo rendimenti della sola componente short
        short_signals = np.where(positions.shift(1) == 0, -1, 0)
        hedge_only_returns = returns * pd.Series(short_signals, index=data.index) * -1
        
        results = {
            'long_only': long_only_equity.dropna(),
            'hedged': hedged_equity.dropna(),
            'hedge_only_returns': hedge_only_returns.dropna(),
            'signal': strategy_signal # Manteniamo il segnale originale per coerenza
        }
        return results

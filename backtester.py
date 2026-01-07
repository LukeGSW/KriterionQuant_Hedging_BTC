# File: backtester.py
# Versione 3.0 - Allineata perfettamente alla logica "Live" (Signal on Close)

import pandas as pd
import numpy as np

class EventDrivenBacktester:
    """
    Esegue un backtest basato su un ciclo (event-driven) che permette
    l'implementazione di logiche complesse come lo stop loss, 
    rispecchiando esattamente la logica del Bot e della Dashboard Live.
    """
    def run_backtest(self, data: pd.DataFrame, strategy_signal: pd.Series, 
                     initial_capital: float, hedge_ratio: float, 
                     stop_loss_perc: float) -> dict:
        """
        Esegue il backtest.
        
        Logica Temporale:
        - I segnali vengono calcolati sul Close della candela 'i'.
        - Se Signal[i] == -1 (Short), si assume entrata al Close[i].
        - Pertanto, la posizione per il giorno 'i+1' sarà Hedged.
        """
        # Array posizioni: 1 = Long (Non Hedged), 0 = Hedged (Flat/Short coperto)
        # Iniziamo tutti Long (1)
        positions = pd.Series(1.0, index=data.index)
        
        # Stato del backtest
        is_hedged = False
        entry_price = 0.0
        
        # Usiamo adj_close per coerenza con i ritorni e il grafico
        price_col = 'adj_close' 

        # Ciclo principale
        # Partiamo da 1 perché guardiamo indietro a i-1
        for i in range(1, len(data)):
            current_close = data[price_col].iloc[i-1] # Close di IERI (prezzo al momento della decisione)
            current_signal = strategy_signal.iloc[i-1] # Segnale generato al Close di IERI
            
            # --- Logica di Uscita (se siamo coperti) ---
            if is_hedged:
                # 1. Stop Loss Check
                # Verifichiamo se il Close di IERI ha violato lo stop rispetto all'entry price
                if current_close > entry_price * (1 + stop_loss_perc):
                    is_hedged = False # Uscita (Stop Loss)
                    entry_price = 0.0
                
                # 2. Signal Exit Check
                # Se il segnale non è più attivo (es. le medie hanno incrociato al rialzo)
                elif current_signal == 0:
                    is_hedged = False # Uscita (Fine Trend)
                    entry_price = 0.0
            
            # --- Logica di Entrata (se NON siamo coperti) ---
            # Nota: Usiamo 'elif' perché se usciamo oggi, rimaniamo flat fino a domani (buco di 1 giorno come nel grafico)
            elif not is_hedged:
                if current_signal == -1:
                    is_hedged = True
                    entry_price = current_close # Entrata al Close di IERI
            
            # Registrazione Posizione per il giorno 'i' (Oggi)
            # Se 'is_hedged' è True, oggi siamo coperti.
            if is_hedged:
                positions.iloc[i] = 0.0 # Hedged
            else:
                positions.iloc[i] = 1.0 # Long Only

        # --- Calcolo Finanziario Vettorizzato ---
        # returns[i] è il rendimento da (i-1) a (i).
        returns = data['adj_close'].pct_change().fillna(0)

        # La posizione che influenza il returns[i] è quella decisa a [i-1]?
        # No, nel loop sopra 'positions[i]' rappresenta lo stato del portafoglio DURANTE il giorno i.
        # Esempio: Se a (i-1) scatta il segnale, il loop setta is_hedged=True, e positions[i]=0.
        # Quindi il rendimento returns[i] (da i-1 a i) verrà moltiplicato per 0 (annullato/coperto). Corretto.
        
        # Rendimento della parte NON coperta (sempre a mercato)
        # Se positions[i] è 1 (Long), prendiamo 100% return. Se è 0 (Hedged), prendiamo (1-hedge_ratio).
        # Ma semplifichiamo:
        # Long Only Part: Sempre 1 * (1 - hedge_ratio)
        # Hedged Part: positions * hedge_ratio
        
        # Se Hedge Ratio = 100% (1.0):
        # Se Long (pos=1): 1 * 1.0 = 100% return.
        # Se Hedged (pos=0): 0 * 1.0 = 0% return.
        
        # Formula Generale per Strategy Returns:
        # (Quota fissa Long) + (Quota variabile gestita)
        # Quota fissa Long = (1 - hedge_ratio)
        # Quota variabile = hedge_ratio * positions
        
        portfolio_exposure = (1 - hedge_ratio) + (hedge_ratio * positions)
        hedged_strategy_returns = returns * portfolio_exposure
        
        # Calcolo curve di equity
        long_only_equity = (1 + returns).cumprod() * initial_capital
        hedged_equity = (1 + hedged_strategy_returns).cumprod() * initial_capital
        
        # Calcolo rendimenti della sola componente short (per KPI)
        # Shortiamo quando positions == 0. Quindi segnale short = (1 - positions) * -1
        short_exposure = (1 - positions) * -1
        hedge_only_returns = returns * short_exposure
        
        results = {
            'long_only': long_only_equity.dropna(),
            'hedged': hedged_equity.dropna(),
            'hedge_only_returns': hedge_only_returns.dropna(),
            'signal': strategy_signal
        }
        return results

# File: streamlit_app.py
# Versione Finale v2: Fix Visualizzazione Posizioni Aperte nel Grafico

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Importa le classi dai nostri moduli di backend
from data_handler import EODHDClient
from indicator_calculator import IndicatorCalculator
from backtester import EventDrivenBacktester
from performance_analyzer import PerformanceAnalyzer

# --- Configurazione della Pagina Streamlit ---
st.set_page_config(
    page_title="Kriterion Quant - Hedging Backtester",
    page_icon="🛡️",
    layout="wide"
)

# --- Parametri Fissi della Strategia Ottimizzata ---
OPTIMAL_PARAMS = {
    'fast_ma': 25, 'slow_ma': 40, 'adx_threshold': 15, 'adx_period': 14
}

# ==============================================================================
# FUNZIONE DI PLOTTING AGGIORNATA (VISUALIZZA ANCHE TRADE APERTI)
# ==============================================================================
def plot_differentiated_signals_on_price(df: pd.DataFrame, ticker: str, stop_loss_perc: float = 0.03):
    """
    Crea un grafico del prezzo con segnali di entrata e uscite differenziate.
    ORA INCLUDE LA VISUALIZZAZIONE DELLA POSIZIONE APERTA CORRENTE.
    """
    trades = []
    in_position = False
    entry_price = 0.0
    entry_date = None
    
    # Variabili per tracciare l'ultima posizione se rimane aperta
    last_open_entry_date = None
    last_open_entry_price = None

    # Nomi colonne per evitare errori
    col_fast = f"sma_{OPTIMAL_PARAMS['fast_ma']}"
    col_slow = f"sma_{OPTIMAL_PARAMS['slow_ma']}"
    col_adx = f"ADX_{OPTIMAL_PARAMS['adx_period']}"

    signal_condition = (df[col_fast] < df[col_slow]) & \
                       (df[col_adx] > OPTIMAL_PARAMS['adx_threshold'])

    for i in range(len(df)):
        current_date = df.index[i]
        current_price = df['adj_close'].iloc[i]

        # Logica di ENTRATA
        if signal_condition.iloc[i] and not in_position:
            in_position = True
            entry_price = current_price
            entry_date = current_date
            # Salviamo questi dati temporaneamente
            last_open_entry_date = current_date
            last_open_entry_price = current_price

        # Logica di USCITA
        elif in_position:
            # 1. STOP LOSS
            if current_price > entry_price * (1 + stop_loss_perc):
                trades.append({
                    'entry_date': entry_date, 'exit_date': current_date,
                    'entry_price': entry_price, 'exit_price': current_price,
                    'exit_reason': 'Stop Loss'
                })
                in_position = False
                last_open_entry_date = None # Reset
            
            # 2. FINE SEGNALE
            elif not signal_condition.iloc[i]:
                trades.append({
                    'entry_date': entry_date, 'exit_date': current_date,
                    'entry_price': entry_price, 'exit_price': current_price,
                    'exit_reason': 'Segnale'
                })
                in_position = False
                last_open_entry_date = None # Reset

    trades_df = pd.DataFrame(trades)
    
    # --- CREAZIONE GRAFICO ---
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['adj_close'], mode='lines', name=f'Prezzo {ticker}', line=dict(color='lightgrey', width=1.5)))

    # 1. Disegna Trade CHIUSI
    if not trades_df.empty:
        # Entrate storiche
        fig.add_trace(go.Scatter(
            x=trades_df['entry_date'], y=trades_df['entry_price'], mode='markers', 
            name='Entrata (Chiusa)', marker=dict(color='red', symbol='triangle-down', size=8, opacity=0.6)
        ))
        
        # Uscite Segnale
        signal_exits = trades_df[trades_df['exit_reason'] == 'Segnale']
        fig.add_trace(go.Scatter(
            x=signal_exits['exit_date'], y=signal_exits['exit_price'], mode='markers', 
            name='Uscita (Segnale)', marker=dict(color='lime', symbol='triangle-up', size=10)
        ))

        # Uscite Stop Loss
        stop_loss_exits = trades_df[trades_df['exit_reason'] == 'Stop Loss']
        fig.add_trace(go.Scatter(
            x=stop_loss_exits['exit_date'], y=stop_loss_exits['exit_price'], mode='markers', 
            name='Uscita (Stop Loss)', marker=dict(color='purple', symbol='x', size=10)
        ))

    # 2. Disegna Trade APERTO (se presente) [FIX CRITICO]
    if in_position and last_open_entry_date is not None:
        fig.add_trace(go.Scatter(
            x=[last_open_entry_date], y=[last_open_entry_price], mode='markers',
            name='ENTRATA CORRENTE (APERTA)', 
            marker=dict(color='red', symbol='triangle-down', size=14, line=dict(width=2, color='white'))
        ))
        # Aggiungiamo un'annotazione per renderlo evidente
        fig.add_annotation(
            x=last_open_entry_date, y=last_open_entry_price,
            text="In Posizione", showarrow=True, arrowhead=1, yshift=-15
        )

    fig.update_layout(title='Prezzo e Segnali di Copertura (1 Anno)', legend_title='Legenda', template='plotly_dark')
    return fig

# ==============================================================================
# FUNZIONI TAB (Logica invariata, solo integrata con il nuovo plot)
# ==============================================================================

def render_live_signal_tab(ticker: str, run_signal: bool):
    st.subheader("Stato Attuale del Segnale e Analisi a 1 Anno")
    if not run_signal:
        st.info("Premi 'Aggiorna Segnale' nella sidebar per visualizzare i dati.")
        return

    with st.spinner("Recupero e analisi dati recenti..."):
        try:
            api_key = st.secrets["EODHD_API_KEY"]
            client = EODHDClient()
            live_start_date = (datetime.now() - timedelta(days=500)).strftime('%Y-%m-%d')
            data_df = client.get_historical_data(api_key, ticker, live_start_date)
        except Exception as e:
            st.error(f"Errore nel recupero dei dati: {e}"); data_df = None
        
        if data_df is not None and not data_df.empty:
            calc = IndicatorCalculator()
            data_df = calc.add_moving_average(data_df, period=OPTIMAL_PARAMS['fast_ma'])
            data_df = calc.add_moving_average(data_df, period=OPTIMAL_PARAMS['slow_ma'])
            data_df = calc.add_adx(data_df, period=OPTIMAL_PARAMS['adx_period'])
            data_df.dropna(inplace=True)
            
            # --- LOGICA SIMULAZIONE STATO ---
            col_fast = f"sma_{OPTIMAL_PARAMS['fast_ma']}"
            col_slow = f"sma_{OPTIMAL_PARAMS['slow_ma']}"
            col_adx = f"ADX_{OPTIMAL_PARAMS['adx_period']}"

            in_position = False
            entry_price = 0.0
            stop_loss_perc = 0.03
            exit_reason = ""

            signal_condition_series = (data_df[col_fast] < data_df[col_slow]) & \
                                      (data_df[col_adx] > OPTIMAL_PARAMS['adx_threshold'])

            for i in range(len(data_df)):
                current_price = data_df['adj_close'].iloc[i]
                is_signal = signal_condition_series.iloc[i]

                if is_signal and not in_position:
                    in_position = True
                    entry_price = current_price
                    exit_reason = "" 
                
                elif in_position:
                    if current_price > entry_price * (1 + stop_loss_perc):
                        in_position = False
                        exit_reason = "Stop Loss Scattato"
                    elif not is_signal:
                        in_position = False
                        exit_reason = "Segnale Terminato"
            
            # --- VISUALIZZAZIONE TESTO ---
            if in_position: 
                st.metric("Stato Attuale", "COPERTURA ATTIVA", delta="Posizione Aperta", delta_color="inverse")
            else: 
                label_stato = "NESSUNA COPERTURA"
                delta_msg = exit_reason if exit_reason else "Attesa Segnale"
                st.metric("Stato Attuale", label_stato, delta=delta_msg, delta_color="off")

            st.markdown(f"Ultimo aggiornamento dati: **{data_df.index[-1].strftime('%d-%m-%Y')}**")
            st.markdown("---")
            
            # --- VISUALIZZAZIONE GRAFICO ---
            data_last_year = data_df.last('365D')
            st.subheader("Grafico Prezzo e Segnali di Copertura (1 Anno)")
            
            # Qui chiamiamo la nuova funzione che disegna anche il trade aperto
            fig_signals = plot_differentiated_signals_on_price(data_last_year, ticker, stop_loss_perc=stop_loss_perc)
            st.plotly_chart(fig_signals, use_container_width=True)
            
            # Grafici ausiliari
            st.subheader("Grafico Prezzo e Medie Mobili (1 Anno)")
            fig_price = go.Figure()
            fig_price.add_trace(go.Scatter(x=data_last_year.index, y=data_last_year['adj_close'], mode='lines', name='Prezzo', line=dict(color='black', width=2)))
            fig_price.add_trace(go.Scatter(x=data_last_year.index, y=data_last_year[col_fast], mode='lines', name=f"SMA({OPTIMAL_PARAMS['fast_ma']})"))
            fig_price.add_trace(go.Scatter(x=data_last_year.index, y=data_last_year[col_slow], mode='lines', name=f"SMA({OPTIMAL_PARAMS['slow_ma']})"))
            st.plotly_chart(fig_price, use_container_width=True)
            
            st.subheader("Grafico ADX (1 Anno)")
            fig_adx = go.Figure()
            fig_adx.add_trace(go.Scatter(x=data_last_year.index, y=data_last_year[col_adx], mode='lines', name='ADX'))
            fig_adx.add_shape(type="line", x0=data_last_year.index[0], y0=OPTIMAL_PARAMS['adx_threshold'], x1=data_last_year.index[-1], y1=OPTIMAL_PARAMS['adx_threshold'], line=dict(color="Red", dash="dash"))
            st.plotly_chart(fig_adx, use_container_width=True)
        else:
            st.warning("Non è stato possibile recuperare i dati recenti.")

def render_historical_backtest_tab(ticker, start_date, capital, hedge_ratio, sl_perc, run_backtest):
    st.subheader("Simulatore di Performance Storica")
    if not run_backtest:
        st.info("Imposta i parametri nella sidebar e premi 'Esegui Backtest'.")
        return
        
    with st.spinner("Esecuzione backtest..."):
        try:
            api_key = st.secrets["EODHD_API_KEY"]
            client = EODHDClient()
            data_df = client.get_historical_data(api_key, ticker, start_date.strftime('%Y-%m-%d'))
        except Exception as e:
            st.error(f"Errore dati: {e}"); data_df = None

        if data_df is not None and not data_df.empty:
            calc = IndicatorCalculator()
            data_df = calc.add_moving_average(data_df, period=OPTIMAL_PARAMS['fast_ma'])
            data_df = calc.add_moving_average(data_df, period=OPTIMAL_PARAMS['slow_ma'])
            data_df = calc.add_adx(data_df, period=OPTIMAL_PARAMS['adx_period'])
            data_df.dropna(inplace=True)
            
            col_fast = f"sma_{OPTIMAL_PARAMS['fast_ma']}"
            col_slow = f"sma_{OPTIMAL_PARAMS['slow_ma']}"
            col_adx = f"ADX_{OPTIMAL_PARAMS['adx_period']}"

            base_signal = np.where((data_df[col_fast] < data_df[col_slow]) & (data_df[col_adx] > OPTIMAL_PARAMS['adx_threshold']), -1, 0)
            backtester = EventDrivenBacktester()
            results = backtester.run_backtest(data_df, pd.Series(base_signal, index=data_df.index), capital, hedge_ratio, sl_perc)
            
            analyzer_hedged = PerformanceAnalyzer(results['hedged'], results['signal'], hedge_only_returns=results['hedge_only_returns'])
            kpis_hedged = analyzer_hedged.calculate_kpis()
            
            positions_bh = pd.Series(1, index=results['long_only'].index)
            analyzer_bh = PerformanceAnalyzer(results['long_only'], positions_bh)
            kpis_bh = analyzer_bh.calculate_kpis()
            
            st.success("Backtest completato!")
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=results['hedged'].index, y=results['hedged'], mode='lines', name='Hedged'))
            fig.add_trace(go.Scatter(x=results['long_only'].index, y=results['long_only'], mode='lines', name='Buy & Hold'))
            st.plotly_chart(fig, use_container_width=True)
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("##### Strategia Coperta")
                kpi_df_hedged = pd.DataFrame.from_dict(kpis_hedged, orient='index', columns=['Valore'])
                for col in ['Max Drawdown', 'Short-Only MaxDD']:
                     if col in kpi_df_hedged.index:
                        kpi_df_hedged.loc[col] = kpi_df_hedged.loc[col].apply(lambda x: f"{x:.2%}" if isinstance(x, (int, float)) else x)
                st.table(kpi_df_hedged)
            with col2:
                st.markdown("##### Benchmark")
                kpis_bh.pop('Short-Only MaxDD', None)
                kpi_df_bh = pd.DataFrame.from_dict(kpis_bh, orient='index', columns=['Valore'])
                if 'Max Drawdown' in kpi_df_bh.index:
                     kpi_df_bh.loc['Max Drawdown'] = f"{kpi_df_bh.loc['Max Drawdown'].values[0]:.2%}"
                st.table(kpi_df_bh)
        else:
            st.warning("Dati non disponibili.")

def render_methodology_tab():
    st.header("Metodologia")
    st.markdown("Questa app implementa una strategia di hedging su Bitcoin.")
    st.code(f"OPTIMAL_PARAMS = {OPTIMAL_PARAMS}", language="python")

# ==============================================================================
# MAIN APP STRUCTURE
# ==============================================================================
st.title("🛡️ Kriterion Quant Hedging Backtester")
st.sidebar.title("Navigazione")
active_tab = st.sidebar.radio("Sezione:", ["Segnale Attuale", "Backtest Storico", "Metodologia"])

if active_tab == "Segnale Attuale":
    st.sidebar.subheader("Controlli")
    ticker = st.sidebar.text_input("Ticker", "BTC-USD.CC")
    if st.sidebar.button("Aggiorna Segnale"):
        render_live_signal_tab(ticker, True)

elif active_tab == "Backtest Storico":
    st.sidebar.subheader("Controlli")
    ticker = st.sidebar.text_input("Ticker", "BTC-USD.CC", key="bt_tick")
    start_dt = st.sidebar.date_input("Inizio", pd.to_datetime("2017-01-01"))
    cap = st.sidebar.number_input("Capitale", value=50000)
    hedge = st.sidebar.slider("Hedge %", 0, 200, 100) / 100.0
    sl = st.sidebar.slider("Stop Loss %", 0, 50, 3) / 100.0
    if st.sidebar.button("Esegui Backtest", type="primary"):
        render_historical_backtest_tab(ticker, start_dt, cap, hedge, sl, True)

elif active_tab == "Metodologia":
    render_methodology_tab()

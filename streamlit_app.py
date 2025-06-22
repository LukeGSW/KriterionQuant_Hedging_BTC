# File: streamlit_app.py
# Versione Finale con Stop Loss default al 6% e Grafico Segnali Live.

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
# NUOVA FUNZIONE DI PLOTTING PER I SEGNALI
# ==============================================================================
def plot_signals_on_price(df: pd.DataFrame, ticker: str):
    """
    Crea un grafico del prezzo con i segnali di entrata e uscita dalla copertura.
    """
    df['signal'] = np.where((df[f"sma_{OPTIMAL_PARAMS['fast_ma']}"] < df[f"sma_{OPTIMAL_PARAMS['slow_ma']}"]) & (df[f"ADX_{OPTIMAL_PARAMS['adx_period']}"] > OPTIMAL_PARAMS['adx_threshold']), 1, 0)
    df['signal_changed'] = df['signal'].diff()

    entries = df[df['signal_changed'] == 1]
    exits = df[df['signal_changed'] == -1]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['adj_close'], mode='lines', name=f'Prezzo {ticker}', line=dict(color='lightgrey', width=1.5)))
    fig.add_trace(go.Scatter(x=entries.index, y=entries['adj_close'], mode='markers', name='Entrata in Copertura', marker=dict(color='red', symbol='triangle-down', size=10)))
    fig.add_trace(go.Scatter(x=exits.index, y=exits['adj_close'], mode='markers', name='Uscita dalla Copertura', marker=dict(color='lime', symbol='triangle-up', size=10)))
    fig.update_layout(title='Prezzo e Segnali di Copertura (1 Anno)', legend_title='Legenda', template='plotly_dark')
    return fig

# ==============================================================================
# DEFINIZIONE DELLE FUNZIONI PER LE TAB
# ==============================================================================

def render_live_signal_tab(ticker: str, run_signal: bool):
    """Renderizza la tab 'Segnale Attuale'."""
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
            
            last_row = data_df.iloc[-1]
            signal_active = (last_row[f"sma_{OPTIMAL_PARAMS['fast_ma']}"] < last_row[f"sma_{OPTIMAL_PARAMS['slow_ma']}"]) and (last_row[f"ADX_{OPTIMAL_PARAMS['adx_period']}"] > OPTIMAL_PARAMS['adx_threshold'])

            if signal_active: st.metric("Stato Attuale", "COPERTURA ATTIVA", delta="Rischio Mitigato", delta_color="inverse")
            else: st.metric("Stato Attuale", "NESSUNA COPERTURA", delta="Posizione Long", delta_color="normal")
            st.markdown(f"Ultimo aggiornamento dati: **{data_df.index[-1].strftime('%d-%m-%Y')}**")
            
            st.markdown("---")
            data_last_year = data_df.last('365D')

            # --- NUOVO GRAFICO AGGIUNTO QUI ---
            st.subheader("Grafico Prezzo e Segnali di Copertura (1 Anno)")
            fig_signals = plot_signals_on_price(data_last_year, ticker)
            st.plotly_chart(fig_signals, use_container_width=True)
            
            # Grafici esistenti
            st.subheader("Grafico Prezzo e Medie Mobili (1 Anno)")
            fig_price = go.Figure()
            fig_price.add_trace(go.Scatter(x=data_last_year.index, y=data_last_year['adj_close'], mode='lines', name='Prezzo', line=dict(color='black', width=2)))
            fig_price.add_trace(go.Scatter(x=data_last_year.index, y=data_last_year[f"sma_{OPTIMAL_PARAMS['fast_ma']}"], mode='lines', name=f"SMA({OPTIMAL_PARAMS['fast_ma']})"))
            fig_price.add_trace(go.Scatter(x=data_last_year.index, y=data_last_year[f"sma_{OPTIMAL_PARAMS['slow_ma']}"], mode='lines', name=f"SMA({OPTIMAL_PARAMS['slow_ma']})"))
            fig_price.update_layout(title='Prezzo e Medie Mobili', legend_title='Legenda')
            st.plotly_chart(fig_price, use_container_width=True)
            
            st.subheader("Grafico ADX (1 Anno)")
            fig_adx = go.Figure()
            fig_adx.add_trace(go.Scatter(x=data_last_year.index, y=data_last_year[f"ADX_{OPTIMAL_PARAMS['adx_period']}"], mode='lines', name='ADX'))
            fig_adx.add_shape(type="line", x0=data_last_year.index[0], y0=OPTIMAL_PARAMS['adx_threshold'], x1=data_last_year.index[-1], y1=OPTIMAL_PARAMS['adx_threshold'], line=dict(color="Red", dash="dash"))
            fig_adx.update_layout(title=f"Indicatore ADX({OPTIMAL_PARAMS['adx_period']}) e Soglia di Trend", legend_title='Legenda')
            st.plotly_chart(fig_adx, use_container_width=True)
        else:
            st.warning("Non è stato possibile recuperare i dati recenti per il ticker specificato.")

# ... Le funzioni render_historical_backtest_tab e render_methodology_tab non cambiano ...
# (ometto per brevità, ma devono rimanere nel tuo file)

# ==============================================================================
# STRUTTURA PRINCIPALE DELL'APP
# ==============================================================================
st.title("🛡️ Kriterion Quant Hedging Backtester")

st.sidebar.title("Navigazione")
active_tab = st.sidebar.radio("Seleziona una sezione:", ["Segnale Attuale", "Backtest Storico", "Metodologia"])

if active_tab == "Segnale Attuale":
    st.sidebar.subheader("Controlli Segnale")
    ticker_live = st.sidebar.text_input("Ticker", "BTC-USD.CC", key="live_ticker")
    run_live_button = st.sidebar.button("Aggiorna Segnale")
    render_live_signal_tab(ticker_live, run_live_button)

elif active_tab == "Backtest Storico":
    st.sidebar.subheader("Controlli Backtest")
    ticker_backtest = st.sidebar.text_input("Ticker", "BTC-USD.CC", key="backtest_ticker")
    start_date_backtest = st.sidebar.date_input("Data di Inizio", pd.to_datetime("2017-01-01"), key="backtest_start_date")
    initial_capital_backtest = st.sidebar.number_input("Capitale Iniziale ($)", min_value=1000, value=50000, step=1000, key="backtest_capital")
    hedge_ratio_backtest = st.sidebar.slider("Rapporto di Copertura (%)", 0, 200, 100, key="backtest_hedge_ratio") / 100.0
    
    # --- MODIFICA STOP LOSS DEFAULT ---
    stop_loss_perc_backtest = st.sidebar.slider("Stop Loss sulle Coperture (%)", 0, 50, 6, help="Impostare a 0 per disattivare lo stop loss.") / 100.0
    
    run_backtest_button = st.sidebar.button("Esegui Backtest", type="primary")
    render_historical_backtest_tab(ticker_backtest, start_date_backtest, initial_capital_backtest, hedge_ratio_backtest, stop_loss_perc_backtest, run_backtest_button)

elif active_tab == "Metodologia":
    render_methodology_tab()

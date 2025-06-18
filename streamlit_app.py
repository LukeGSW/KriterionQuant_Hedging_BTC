# File: streamlit_app.py
# Versione Ristrutturata con Architettura a Tab

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Importa le classi dai nostri moduli di backend
from data_handler import EODHDClient
from indicator_calculator import IndicatorCalculator
from backtester import VectorizedBacktester
from performance_analyzer import PerformanceAnalyzer

# --- Configurazione della Pagina Streamlit ---
st.set_page_config(
    page_title="Kriterion Quant - Hedging Backtester",
    page_icon="🛡️",
    layout="wide"
)

# --- Parametri Fissi della Strategia Ottimizzata ---
# Questi sono i parametri che abbiamo "bloccato" dopo la fase di ottimizzazione
# per la strategia Trend_Momentum_ADX
OPTIMAL_PARAMS = {
    'fast_ma': 35,       # Sostituire con il valore scelto
    'slow_ma': 100,      # Sostituire con il valore scelto
    'adx_threshold': 20, # Sostituire con il valore scelto
    'adx_period': 14
}

# ==============================================================================
# FUNZIONE PER LA TAB "BACKTEST STORICO"
# ==============================================================================
def render_historical_backtest_tab():
    st.subheader("Simulatore di Performance Storica")
    st.markdown("Usa i controlli nella sidebar per configurare e lanciare un backtest completo della strategia con i parametri ottimizzati.")

    # --- Sidebar per Input Utente del Backtest ---
    st.sidebar.title("Parametri Backtest Storico")
    ticker = st.sidebar.text_input("Ticker", "BTC-USD.CC", key="backtest_ticker")
    start_date = st.sidebar.date_input("Data di Inizio", pd.to_datetime("2018-01-01"), key="backtest_start_date")
    initial_capital = st.sidebar.number_input("Capitale Iniziale ($)", min_value=1000, value=50000, step=1000, key="backtest_capital")
    hedge_ratio = st.sidebar.slider("Rapporto di Copertura (%)", 0, 200, 100, key="backtest_hedge_ratio") / 100.0

    run_button = st.sidebar.button("Esegui Backtest", type="primary")

    if run_button:
        with st.spinner("Esecuzione del backtest storico..."):
            # 1. Recupero Dati
            try:
                api_key = st.secrets["EODHD_API_KEY"]
                client = EODHDClient()
                data_df = client.get_historical_data(api_key, ticker, start_date.strftime('%Y-%m-%d'))
            except Exception as e:
                st.error(f"Errore nel recupero dei dati: {e}")
                data_df = None

            if data_df is not None and not data_df.empty:
                # 2. Calcolo Indicatori
                calc = IndicatorCalculator()
                data_df = calc.add_moving_average(data_df, period=OPTIMAL_PARAMS['fast_ma'])
                data_df = calc.add_moving_average(data_df, period=OPTIMAL_PARAMS['slow_ma'])
                data_df = calc.add_adx(data_df, period=OPTIMAL_PARAMS['adx_period'])
                data_df.dropna(inplace=True)

                # 3. Generazione Segnale e Backtest
                signal = np.where(
                    (data_df[f"sma_{OPTIMAL_PARAMS['fast_ma']}"] < data_df[f"sma_{OPTIMAL_PARAMS['slow_ma']}"]) & 
                    (data_df[f"ADX_{OPTIMAL_PARAMS['adx_period']}"] > OPTIMAL_PARAMS['adx_threshold']), 
                    -1, 0
                )
                backtester = VectorizedBacktester()
                results = backtester.run_backtest(data_df, pd.Series(signal, index=data_df.index), initial_capital, hedge_ratio)

                # 4. Calcolo Performance e Visualizzazione
                analyzer = PerformanceAnalyzer(results['hedged'], results['signal'], hedge_only_returns=results['hedge_only_returns'])
                kpis = analyzer.calculate_kpis()
                
                st.success("Backtest completato!")
                
                # Visualizzazione KPI principali
                col1, col2, col3 = st.columns(3)
                col1.metric("Net Profit", f"${kpis['Net Profit']:,.2f}")
                col2.metric("Profit Factor", f"{kpis['Profit Factor']:.2f}")
                col3.metric("Sharpe Ratio", f"{kpis['Sharpe Ratio']:.2f}")
                
                # Grafico Equity Line
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=results['hedged'].index, y=results['hedged'], mode='lines', name='Strategia Coperta (Hedged)'))
                fig.add_trace(go.Scatter(x=results['long_only'].index, y=results['long_only'], mode='lines', name='Buy & Hold (Benchmark)'))
                fig.update_layout(title='Andamento del Portafoglio', xaxis_title='Data', yaxis_title='Valore Portafoglio ($)', legend_title='Strategia')
                st.plotly_chart(fig, use_container_width=True)

                # Tabella completa dei KPI
                st.subheader("Metriche di Performance Dettagliate")
                kpi_df = pd.DataFrame.from_dict(kpis, orient='index', columns=['Valore'])
                kpi_df.loc[['Max Drawdown', 'Short-Only MaxDD']] = kpi_df.loc[['Max Drawdown', 'Short-Only MaxDD']].applymap(lambda x: f"{x:.2%}")
                st.table(kpi_df)

            else:
                st.warning("Non è stato possibile recuperare i dati per il ticker specificato.")

# ==============================================================================
# FUNZIONE PER LA TAB "SEGNALE ATTUALE" (DA IMPLEMENTARE)
# ==============================================================================
def render_live_signal_tab():
    st.header("Segnale Attuale e Grafici a 1 Anno")
    st.info("Questa sezione è in fase di sviluppo. Mostrerà lo stato del segnale più recente e i grafici di prezzo e indicatori dell'ultimo anno.", icon="🚧")

# ==============================================================================
# FUNZIONE PER LA TAB "METODOLOGIA" (DA IMPLEMENTARE)
# ==============================================================================
def render_methodology_tab():
    st.header("Metodologia della Strategia")
    st.info("Questa sezione è in fase di sviluppo. Conterrà la descrizione dettagliata delle regole della strategia e dei parametri utilizzati.", icon="🚧")


# ==============================================================================
# STRUTTURA PRINCIPALE DELL'APP
# ==============================================================================
st.title("🛡️ Kriterion Quant Hedging Backtester")

live_tab, backtest_tab, methodology_tab = st.tabs(["Segnale Attuale", "Backtest Storico", "Metodologia"])

with live_tab:
    render_live_signal_tab()

with backtest_tab:
    render_historical_backtest_tab()

with methodology_tab:
    render_methodology_tab()

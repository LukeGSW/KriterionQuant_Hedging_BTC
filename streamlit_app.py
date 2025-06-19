# File: streamlit_app.py (Versione con Stop Loss)

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# MODIFICA: Importiamo il nuovo backtester
from backtester import EventDrivenBacktester
from data_handler import EODHDClient
from indicator_calculator import IndicatorCalculator
from performance_analyzer import PerformanceAnalyzer

st.set_page_config(page_title="Kriterion Quant - Hedging Backtester", page_icon="🛡️", layout="wide")

OPTIMAL_PARAMS = {
    'fast_ma': 30, 'slow_ma': 50, 'adx_threshold': 15, 'adx_period': 14
}

def render_historical_backtest_tab():
    st.subheader("Simulatore di Performance Storica")
    st.markdown("Usa i controlli nella sidebar per configurare e lanciare un backtest completo.")

    st.sidebar.title("Parametri Backtest Storico")
    ticker = st.sidebar.text_input("Ticker", "BTC-USD.CC", key="backtest_ticker")
    start_date = st.sidebar.date_input("Data di Inizio", pd.to_datetime("2018-01-01"), key="backtest_start_date")
    initial_capital = st.sidebar.number_input("Capitale Iniziale ($)", min_value=1000, value=50000, step=1000, key="backtest_capital")
    hedge_ratio = st.sidebar.slider("Rapporto di Copertura (%)", 0, 200, 100, key="backtest_hedge_ratio") / 100.0
    
    # --- NUOVO WIDGET: Stop Loss ---
    stop_loss_perc = st.sidebar.slider("Stop Loss sulle Coperture (%)", 0, 50, 10, help="Se una posizione short perde questa percentuale, viene chiusa.") / 100.0

    run_button = st.sidebar.button("Esegui Backtest", type="primary")

    if run_button:
        with st.spinner("Esecuzione del backtest..."):
            try:
                api_key = st.secrets["EODHD_API_KEY"]
                client = EODHDClient()
                data_df = client.get_historical_data(api_key, ticker, start_date.strftime('%Y-%m-%d'))
            except Exception as e:
                st.error(f"Errore nel recupero dei dati: {e}"); data_df = None

            if data_df is not None and not data_df.empty:
                calc = IndicatorCalculator()
                data_df = calc.add_moving_average(data_df, period=OPTIMAL_PARAMS['fast_ma'])
                data_df = calc.add_moving_average(data_df, period=OPTIMAL_PARAMS['slow_ma'])
                data_df = calc.add_adx(data_df, period=OPTIMAL_PARAMS['adx_period'])
                data_df.dropna(inplace=True)

                base_signal = np.where(
                    (data_df[f"sma_{OPTIMAL_PARAMS['fast_ma']}"] < data_df[f"sma_{OPTIMAL_PARAMS['slow_ma']}"]) & 
                    (data_df[f"ADX_{OPTIMAL_PARAMS['adx_period']}"] > OPTIMAL_PARAMS['adx_threshold']), -1, 0)
                
                # --- MODIFICA: Usiamo il nuovo backtester e passiamo lo stop loss ---
                backtester = EventDrivenBacktester()
                results = backtester.run_backtest(
                    data_df, 
                    pd.Series(base_signal, index=data_df.index), 
                    initial_capital, 
                    hedge_ratio, 
                    stop_loss_perc
                )
                
                # Il resto della visualizzazione rimane invariato
                analyzer = PerformanceAnalyzer(results['hedged'], results['signal'], hedge_only_returns=results['hedge_only_returns'])
                kpis = analyzer.calculate_kpis()
                
                st.success("Backtest completato!")
                col1, col2, col3 = st.columns(3)
                col1.metric("Net Profit", f"${kpis['Net Profit']:,.2f}")
                col2.metric("Profit Factor", f"{kpis['Profit Factor']:.2f}")
                col3.metric("Sharpe Ratio", f"{kpis['Sharpe Ratio']:.2f}")
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=results['hedged'].index, y=results['hedged'], mode='lines', name='Strategia Coperta (Hedged)'))
                fig.add_trace(go.Scatter(x=results['long_only'].index, y=results['long_only'], mode='lines', name='Buy & Hold (Benchmark)'))
                fig.update_layout(title='Andamento del Portafoglio', xaxis_title='Data', yaxis_title='Valore Portafoglio ($)', legend_title='Strategia')
                st.plotly_chart(fig, use_container_width=True)

                st.subheader("Metriche di Performance Dettagliate")
                kpi_df = pd.DataFrame.from_dict(kpis, orient='index', columns=['Valore'])
                kpi_df.loc[['Max Drawdown', 'Short-Only MaxDD']] = kpi_df.loc[['Max Drawdown', 'Short-Only MaxDD']].applymap(lambda x: f"{x:.2%}")
                st.table(kpi_df)
            else:
                st.warning("Non è stato possibile recuperare i dati per il ticker specificato.")

# Funzioni placeholder per le altre tab
def render_live_signal_tab():
    st.header("Segnale Attuale e Grafici a 1 Anno")
    st.info("Questa sezione è in fase di sviluppo.", icon="🚧")
def render_methodology_tab():
    st.header("Metodologia della Strategia")
    st.info("Questa sezione è in fase di sviluppo.", icon="🚧")

# Struttura principale dell'app
st.title("🛡️ Kriterion Quant Hedging Backtester")
live_tab, backtest_tab, methodology_tab = st.tabs(["Segnale Attuale", "Backtest Storico", "Metodologia"])
with live_tab: render_live_signal_tab()
with backtest_tab: render_historical_backtest_tab()
with methodology_tab: render_methodology_tab()

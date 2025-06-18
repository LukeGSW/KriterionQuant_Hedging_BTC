# File: streamlit_app.py
# Modulo per il progetto KriterionQuant Hedging App

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

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

# --- Titolo e Introduzione ---
st.title("🛡️ Kriterion Quant Hedging Backtester")
st.markdown("""
Questa applicazione esegue un backtest di una strategia di hedging per un asset finanziario (default: Bitcoin).
La strategia utilizzata è la **Trend_Momentum_ADX**, che si è dimostrata la più robusta nella fase di ricerca.
Utilizza i controlli nella barra laterale per personalizzare la simulazione.
""")

# --- Parametri Fissi della Strategia Ottimizzata ---
# Questi sono i parametri che abbiamo "bloccato" dopo la fase di ottimizzazione
OPTIMAL_PARAMS = {
    'fast_ma': 20,       # Sostituire con il valore scelto
    'slow_ma': 60,       # Sostituire con il valore scelto
    'adx_threshold': 25, # Sostituire con il valore scelto
    'adx_period': 14
}

# --- Sidebar per Input Utente ---
st.sidebar.title("Parametri di Simulazione")
ticker = st.sidebar.text_input("Ticker", "BTC-USD.CC")
start_date = st.sidebar.date_input("Data di Inizio", pd.to_datetime("2018-01-01"))
initial_capital = st.sidebar.number_input("Capitale Iniziale ($)", min_value=1000, value=50000, step=1000)
hedge_ratio = st.sidebar.slider("Rapporto di Copertura (%)", 0, 200, 100) / 100.0

run_button = st.sidebar.button("Esegui Analisi", type="primary")

# --- Logica Principale dell'Applicazione ---
if run_button:
    with st.spinner("Analisi in corso... Potrebbe richiedere qualche secondo."):
        # 1. Recupero Dati
        try:
            # Gestione sicura della chiave API tramite i secrets di Streamlit
            api_key = st.secrets["EODHD_API_KEY"]
            client = EODHDClient()
            data_df = client.get_historical_data(api_key, ticker, start_date.strftime('%Y-%m-%d'))
        except Exception as e:
            st.error(f"Errore nel recupero dei dati: {e}")
            data_df = None

        if data_df is not None and not data_df.empty:
            # 2. Calcolo Indicatori con i parametri OTTIMALI
            calc = IndicatorCalculator()
            data_df = calc.add_moving_average(data_df, period=OPTIMAL_PARAMS['fast_ma'])
            data_df = calc.add_moving_average(data_df, period=OPTIMAL_PARAMS['slow_ma'])
            data_df = calc.add_adx(data_df, period=OPTIMAL_PARAMS['adx_period'])
            data_df.dropna(inplace=True)

            # 3. Generazione Segnale e Backtest con HEDGE RATIO DINAMICO
            signal = np.where(
                (data_df[f"sma_{OPTIMAL_PARAMS['fast_ma']}"] < data_df[f"sma_{OPTIMAL_PARAMS['slow_ma']}"]) & 
                (data_df[f"ADX_{OPTIMAL_PARAMS['adx_period']}"] > OPTIMAL_PARAMS['adx_threshold']), 
                -1, 0
            )
            
            backtester = VectorizedBacktester()
            results = backtester.run_backtest(data_df, pd.Series(signal, index=data_df.index), initial_capital, hedge_ratio)

            # 4. Calcolo Performance e Visualizzazione
            analyzer = PerformanceAnalyzer(
                results['hedged'], 
                results['signal'], 
                hedge_only_returns=results['hedge_only_returns']
            )
            kpis = analyzer.calculate_kpis()
            
            st.success("Analisi completata con successo!")
            st.header(f"Risultati per {ticker}")

            # Visualizzazione KPI
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
            kpi_df = pd.DataFrame.from_dict(kpis, orient='index', columns=['Value'])
            kpi_df.loc[['Max Drawdown', 'Short-Only MaxDD']] = kpi_df.loc[['Max Drawdown', 'Short-Only MaxDD']].applymap(lambda x: f"{x:.2%}")
            st.table(kpi_df)

        else:
            st.warning("Non è stato possibile recuperare i dati per il ticker specificato. Controllare il ticker o l'intervallo di date.")

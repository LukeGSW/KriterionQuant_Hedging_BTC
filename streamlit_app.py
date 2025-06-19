# File: streamlit_app.py
# Versione Finale e Completa con tutte le tab implementate

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
# Questi sono i parametri che abbiamo "bloccato" dopo la fase di ottimizzazione
# per la strategia Trend_Momentum_ADX
OPTIMAL_PARAMS = {
    'fast_ma': 30,
    'slow_ma': 50,
    'adx_threshold': 15,
    'adx_period': 14
}

# ==============================================================================
# FUNZIONE PER LA TAB "SEGNALE ATTUALE"
# ==============================================================================
def render_live_signal_tab():
    st.subheader("Stato Attuale del Segnale e Analisi a 1 Anno")

    # Sidebar per questa tab specifica
    st.sidebar.title("Parametri Segnale Attuale")
    ticker_live = st.sidebar.text_input("Ticker", "BTC-USD.CC", key="live_ticker")
    run_live_button = st.sidebar.button("Aggiorna Segnale", type="primary")

    if run_live_button:
        with st.spinner("Recupero e analisi dati recenti..."):
            # 1. Recupero Dati Recenti (ultimi ~18 mesi per avere storico per indicatori)
            try:
                api_key = st.secrets["EODHD_API_KEY"]
                client = EODHDClient()
                live_start_date = (datetime.now() - timedelta(days=500)).strftime('%Y-%m-%d')
                data_df = client.get_historical_data(api_key, ticker_live, live_start_date)
            except Exception as e:
                st.error(f"Errore nel recupero dei dati: {e}"); data_df = None
            
            if data_df is not None and not data_df.empty:
                # 2. Calcolo Indicatori
                calc = IndicatorCalculator()
                data_df = calc.add_moving_average(data_df, period=OPTIMAL_PARAMS['fast_ma'])
                data_df = calc.add_moving_average(data_df, period=OPTIMAL_PARAMS['slow_ma'])
                data_df = calc.add_adx(data_df, period=OPTIMAL_PARAMS['adx_period'])
                data_df.dropna(inplace=True)

                # 3. Determinazione Segnale Attuale
                last_row = data_df.iloc[-1]
                signal_active = (last_row[f"sma_{OPTIMAL_PARAMS['fast_ma']}"] < last_row[f"sma_{OPTIMAL_PARAMS['slow_ma']}"]) and (last_row[f"ADX_{OPTIMAL_PARAMS['adx_period']}"] > OPTIMAL_PARAMS['adx_threshold'])

                # 4. Visualizzazione Stato
                if signal_active:
                    st.metric("Stato Attuale", "COPERTURA ATTIVA", delta="Rischio Mitigato", delta_color="inverse")
                else:
                    st.metric("Stato Attuale", "NESSUNA COPERTURA", delta="Posizione Long", delta_color="normal")
                
                st.markdown(f"Ultimo aggiornamento dati: **{data_df.index[-1].strftime('%d-%m-%Y')}**")

                # 5. Grafici a 1 Anno
                data_last_year = data_df.last('365D')
                
                # Grafico Prezzo e Medie Mobili
                st.subheader("Grafico Prezzo e Medie Mobili (1 Anno)")
                fig_price = go.Figure()
                fig_price.add_trace(go.Scatter(x=data_last_year.index, y=data_last_year['adj_close'], mode='lines', name='Prezzo BTC', line=dict(color='black', width=2)))
                fig_price.add_trace(go.Scatter(x=data_last_year.index, y=data_last_year[f"sma_{OPTIMAL_PARAMS['fast_ma']}"], mode='lines', name=f"SMA({OPTIMAL_PARAMS['fast_ma']})"))
                fig_price.add_trace(go.Scatter(x=data_last_year.index, y=data_last_year[f"sma_{OPTIMAL_PARAMS['slow_ma']}"], mode='lines', name=f"SMA({OPTIMAL_PARAMS['slow_ma']})"))
                fig_price.update_layout(title='Prezzo e Medie Mobili', legend_title='Legenda')
                st.plotly_chart(fig_price, use_container_width=True)

                # Grafico ADX
                st.subheader("Grafico ADX (1 Anno)")
                fig_adx = go.Figure()
                fig_adx.add_trace(go.Scatter(x=data_last_year.index, y=data_last_year[f"ADX_{OPTIMAL_PARAMS['adx_period']}"], mode='lines', name='ADX'))
                fig_adx.add_shape(type="line", x0=data_last_year.index[0], y0=OPTIMAL_PARAMS['adx_threshold'], x1=data_last_year.index[-1], y1=OPTIMAL_PARAMS['adx_threshold'], line=dict(color="Red", dash="dash"))
                fig_adx.update_layout(title=f"Indicatore ADX({OPTIMAL_PARAMS['adx_period']}) e Soglia di Trend", legend_title='Legenda')
                st.plotly_chart(fig_adx, use_container_width=True)
            else:
                st.warning("Non è stato possibile recuperare i dati recenti per il ticker specificato.")


# ==============================================================================
# FUNZIONE PER LA TAB "BACKTEST STORICO"
# ==============================================================================
def render_historical_backtest_tab():
    st.subheader("Simulatore di Performance Storica")
    st.markdown("Usa i controlli nella sidebar per configurare e lanciare un backtest completo della strategia con i parametri ottimizzati.")
    
    # ... (Codice della tab di backtest - INVARIATO) ...
    st.sidebar.title("Parametri Backtest Storico")
    ticker_backtest = st.sidebar.text_input("Ticker", "BTC-USD.CC", key="backtest_ticker")
    start_date_backtest = st.sidebar.date_input("Data di Inizio", pd.to_datetime("2017-01-01"), key="backtest_start_date")
    initial_capital_backtest = st.sidebar.number_input("Capitale Iniziale ($)", min_value=1000, value=50000, step=1000, key="backtest_capital")
    hedge_ratio_backtest = st.sidebar.slider("Rapporto di Copertura (%)", 0, 200, 100, key="backtest_hedge_ratio") / 100.0
    stop_loss_perc_backtest = st.sidebar.slider("Stop Loss sulle Coperture (%)", 0, 50, 0, help="Impostare a 0 per disattivare lo stop loss e replicare i risultati del notebook.") / 100.0
    run_backtest_button = st.sidebar.button("Esegui Backtest")

    if run_backtest_button:
        with st.spinner("Esecuzione del backtest storico..."):
            try:
                api_key = st.secrets["EODHD_API_KEY"]
                client = EODHDClient()
                data_df = client.get_historical_data(api_key, ticker_backtest, start_date_backtest.strftime('%Y-%m-%d'))
            except Exception as e:
                st.error(f"Errore nel recupero dei dati: {e}"); data_df = None

            if data_df is not None and not data_df.empty:
                calc = IndicatorCalculator()
                data_df = calc.add_moving_average(data_df, period=OPTIMAL_PARAMS['fast_ma']); data_df = calc.add_moving_average(data_df, period=OPTIMAL_PARAMS['slow_ma']); data_df = calc.add_adx(data_df, period=OPTIMAL_PARAMS['adx_period']); data_df.dropna(inplace=True)
                base_signal = np.where((data_df[f"sma_{OPTIMAL_PARAMS['fast_ma']}"] < data_df[f"sma_{OPTIMAL_PARAMS['slow_ma']}"]) & (data_df[f"ADX_{OPTIMAL_PARAMS['adx_period']}"] > OPTIMAL_PARAMS['adx_threshold']), -1, 0)
                backtester = EventDrivenBacktester()
                results = backtester.run_backtest(data_df, pd.Series(base_signal, index=data_df.index), initial_capital_backtest, hedge_ratio_backtest, stop_loss_perc_backtest)
                analyzer = PerformanceAnalyzer(results['hedged'], results['signal'], hedge_only_returns=results['hedge_only_returns'])
                kpis = analyzer.calculate_kpis()
                
                st.success("Backtest completato!")
                col1, col2, col3 = st.columns(3)
                col1.metric("Net Profit", f"${kpis['Net Profit']:,.2f}"); col2.metric("Profit Factor", f"{kpis['Profit Factor']:.2f}"); col3.metric("Sharpe Ratio", f"{kpis['Sharpe Ratio']:.2f}")
                fig = go.Figure(); fig.add_trace(go.Scatter(x=results['hedged'].index, y=results['hedged'], mode='lines', name='Strategia Coperta (Hedged)')); fig.add_trace(go.Scatter(x=results['long_only'].index, y=results['long_only'], mode='lines', name='Buy & Hold (Benchmark)')); fig.update_layout(title='Andamento del Portafoglio', xaxis_title='Data', yaxis_title='Valore Portafoglio ($)', legend_title='Strategia'); st.plotly_chart(fig, use_container_width=True)
                st.subheader("Metriche di Performance Dettagliate"); kpi_df = pd.DataFrame.from_dict(kpis, orient='index', columns=['Valore']); kpi_df.loc[['Max Drawdown', 'Short-Only MaxDD']] = kpi_df.loc[['Max Drawdown', 'Short-Only MaxDD']].applymap(lambda x: f"{x:.2%}"); st.table(kpi_df)
            else:
                st.warning("Non è stato possibile recuperare i dati per il ticker specificato.")


# ==============================================================================
# FUNZIONE PER LA TAB "METODOLOGIA"
# ==============================================================================
def render_methodology_tab():
    st.header("Metodologia della Strategia e dell'App")
    st.markdown("""
    Questa applicazione è il risultato finale di un processo di ricerca e sviluppo di una strategia di hedging per asset volatili come Bitcoin.
    """)

    st.subheader("Strategia: Trend/Momentum Crossover con Filtro ADX")
    st.markdown("""
    La strategia implementata è stata selezionata come la più robusta dopo una fase di ottimizzazione e validazione. Le sue regole sono:
    - **Condizione di Entrata in Copertura:** Si apre una posizione short (per coprire una parte del portafoglio) quando la media mobile veloce incrocia al ribasso quella lenta E l'indicatore ADX è superiore a una certa soglia, a conferma che è presente un trend definito.
    - **Condizione di Uscita dalla Copertura:** La copertura viene chiusa quando il segnale degli indicatori cessa.
    - **Stop Loss (Opzionale):** Una misura di sicurezza chiude la copertura se il prezzo sale di una certa percentuale, limitando le perdite sulla singola operazione di hedging.
    """)

    st.subheader("Parametri Ottimali Utilizzati")
    st.markdown("I seguenti parametri sono stati 'bloccati' dopo la Fase 2 di ottimizzazione e sono usati come default dall'applicazione:")
    st.code(f"""
OPTIMAL_PARAMS = {{
    'fast_ma': {OPTIMAL_PARAMS['fast_ma']},
    'slow_ma': {OPTIMAL_PARAMS['slow_ma']},
    'adx_threshold': {OPTIMAL_PARAMS['adx_threshold']},
    'adx_period': {OPTIMAL_PARAMS['adx_period']}
}}
    """, language="python")


# ==============================================================================
# STRUTTURA PRINCIPALE DELL'APP
# ==============================================================================
st.title("🛡️ Kriterion Quant Hedging Backtester")

# Gestione dello stato per le tab
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = "Segnale Attuale"

# Creiamo i bottoni per la navigazione
col1, col2, col3 = st.columns(3)
if col1.button("Segnale Attuale"):
    st.session_state.active_tab = "Segnale Attuale"
if col2.button("Backtest Storico"):
    st.session_state.active_tab = "Backtest Storico"
if col3.button("Metodologia"):
    st.session_state.active_tab = "Metodologia"

# Mostriamo il contenuto della tab attiva
if st.session_state.active_tab == "Segnale Attuale":
    render_live_signal_tab()
elif st.session_state.active_tab == "Backtest Storico":
    render_historical_backtest_tab()
elif st.session_state.active_tab == "Metodologia":
    render_methodology_tab()

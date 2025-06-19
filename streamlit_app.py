# File: streamlit_app.py
# Versione Finale con Tabella KPI per Buy & Hold

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
    'fast_ma': 30, 'slow_ma': 50, 'adx_threshold': 20, 'adx_period': 14
}

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
            calc = IndicatorCalculator(); data_df = calc.add_moving_average(data_df, period=OPTIMAL_PARAMS['fast_ma']); data_df = calc.add_moving_average(data_df, period=OPTIMAL_PARAMS['slow_ma']); data_df = calc.add_adx(data_df, period=OPTIMAL_PARAMS['adx_period']); data_df.dropna(inplace=True)
            last_row = data_df.iloc[-1]
            signal_active = (last_row[f"sma_{OPTIMAL_PARAMS['fast_ma']}"] < last_row[f"sma_{OPTIMAL_PARAMS['slow_ma']}"]) and (last_row[f"ADX_{OPTIMAL_PARAMS['adx_period']}"] > OPTIMAL_PARAMS['adx_threshold'])

            if signal_active: st.metric("Stato Attuale", "COPERTURA ATTIVA", delta="Rischio Mitigato", delta_color="inverse")
            else: st.metric("Stato Attuale", "NESSUNA COPERTURA", delta="Posizione Long", delta_color="normal")
            st.markdown(f"Ultimo aggiornamento dati: **{data_df.index[-1].strftime('%d-%m-%Y')}**")
            
            data_last_year = data_df.last('365D')
            st.subheader("Grafico Prezzo e Medie Mobili (1 Anno)"); fig_price = go.Figure(); fig_price.add_trace(go.Scatter(x=data_last_year.index, y=data_last_year['adj_close'], mode='lines', name='Prezzo', line=dict(color='black', width=2))); fig_price.add_trace(go.Scatter(x=data_last_year.index, y=data_last_year[f"sma_{OPTIMAL_PARAMS['fast_ma']}"], mode='lines', name=f"SMA({OPTIMAL_PARAMS['fast_ma']})")); fig_price.add_trace(go.Scatter(x=data_last_year.index, y=data_last_year[f"sma_{OPTIMAL_PARAMS['slow_ma']}"], mode='lines', name=f"SMA({OPTIMAL_PARAMS['slow_ma']})")); fig_price.update_layout(title='Prezzo e Medie Mobili', legend_title='Legenda'); st.plotly_chart(fig_price, use_container_width=True)
            st.subheader("Grafico ADX (1 Anno)"); fig_adx = go.Figure(); fig_adx.add_trace(go.Scatter(x=data_last_year.index, y=data_last_year[f"ADX_{OPTIMAL_PARAMS['adx_period']}"], mode='lines', name='ADX')); fig_adx.add_shape(type="line", x0=data_last_year.index[0], y0=OPTIMAL_PARAMS['adx_threshold'], x1=data_last_year.index[-1], y1=OPTIMAL_PARAMS['adx_threshold'], line=dict(color="Red", dash="dash")); fig_adx.update_layout(title=f"Indicatore ADX({OPTIMAL_PARAMS['adx_period']}) e Soglia di Trend", legend_title='Legenda'); st.plotly_chart(fig_adx, use_container_width=True)
        else:
            st.warning("Non è stato possibile recuperare i dati recenti per il ticker specificato.")

def render_historical_backtest_tab(ticker, start_date, capital, hedge_ratio, sl_perc, run_backtest):
    """Renderizza la tab 'Backtest Storico'."""
    st.subheader("Simulatore di Performance Storica")
    if not run_backtest:
        st.info("Imposta i parametri nella sidebar e premi 'Esegui Backtest' per visualizzare i risultati.")
        return
        
    with st.spinner("Esecuzione del backtest storico..."):
        try:
            api_key = st.secrets["EODHD_API_KEY"]
            client = EODHDClient()
            data_df = client.get_historical_data(api_key, ticker, start_date.strftime('%Y-%m-%d'))
        except Exception as e:
            st.error(f"Errore nel recupero dei dati: {e}"); data_df = None

        if data_df is not None and not data_df.empty:
            calc = IndicatorCalculator(); data_df = calc.add_moving_average(data_df, period=OPTIMAL_PARAMS['fast_ma']); data_df = calc.add_moving_average(data_df, period=OPTIMAL_PARAMS['slow_ma']); data_df = calc.add_adx(data_df, period=OPTIMAL_PARAMS['adx_period']); data_df.dropna(inplace=True)
            base_signal = np.where((data_df[f"sma_{OPTIMAL_PARAMS['fast_ma']}"] < data_df[f"sma_{OPTIMAL_PARAMS['slow_ma']}"]) & (data_df[f"ADX_{OPTIMAL_PARAMS['adx_period']}"] > OPTIMAL_PARAMS['adx_threshold']), -1, 0)
            backtester = EventDrivenBacktester()
            results = backtester.run_backtest(data_df, pd.Series(base_signal, index=data_df.index), capital, hedge_ratio, sl_perc)
            
            # --- MODIFICA INIZIA QUI ---

            # 1. Calcola KPI per la strategia coperta (Hedged)
            analyzer_hedged = PerformanceAnalyzer(results['hedged'], results['signal'], hedge_only_returns=results['hedge_only_returns'])
            kpis_hedged = analyzer_hedged.calculate_kpis()
            
            # 2. Calcola KPI per il benchmark (Buy & Hold)
            # Per il B&H, la posizione è sempre 1 (long). Non ci sono "trade" attivi.
            positions_bh = pd.Series(1, index=results['long_only'].index)
            analyzer_bh = PerformanceAnalyzer(results['long_only'], positions_bh)
            kpis_bh = analyzer_bh.calculate_kpis()
            
            st.success("Backtest completato!")
            
            # Grafico Equity Line (invariato)
            fig = go.Figure(); fig.add_trace(go.Scatter(x=results['hedged'].index, y=results['hedged'], mode='lines', name='Strategia Coperta (Hedged)')); fig.add_trace(go.Scatter(x=results['long_only'].index, y=results['long_only'], mode='lines', name='Buy & Hold (Benchmark)')); fig.update_layout(title='Andamento del Portafoglio', xaxis_title='Data', yaxis_title='Valore Portafoglio ($)', legend_title='Strategia'); st.plotly_chart(fig, use_container_width=True)
            
            st.subheader("Metriche di Performance a Confronto")

            # 3. Creazione delle due tabelle affiancate
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("##### Strategia Coperta (Hedged)")
                kpi_df_hedged = pd.DataFrame.from_dict(kpis_hedged, orient='index', columns=['Valore'])
                kpi_df_hedged.loc[['Max Drawdown', 'Short-Only MaxDD']] = kpi_df_hedged.loc[['Max Drawdown', 'Short-Only MaxDD']].applymap(lambda x: f"{x:.2%}")
                st.table(kpi_df_hedged)

            with col2:
                st.markdown("##### Benchmark (Buy & Hold)")
                # Rimuoviamo le metriche non pertinenti per il B&H
                kpis_bh.pop('Short-Only MaxDD', None)
                kpis_bh['Num Trades'] = 1 # Per convenzione
                kpi_df_bh = pd.DataFrame.from_dict(kpis_bh, orient='index', columns=['Valore'])
                kpi_df_bh.loc['Max Drawdown'] = f"{kpi_df_bh.loc['Max Drawdown'].values[0]:.2%}"
                st.table(kpi_df_bh)

            # --- MODIFICA FINISCE QUI ---
            
        else:
            st.warning("Non è stato possibile recuperare i dati per il ticker specificato.")

def render_methodology_tab():
    """Renderizza la tab 'Metodologia'."""
    st.header("Metodologia della Strategia e dell'App")
    st.markdown("Questa applicazione è il risultato finale di un processo di ricerca e sviluppo di una strategia di hedging per asset volatili come Bitcoin."); st.subheader("Strategia: Trend/Momentum Crossover con Filtro ADX")
    st.markdown("- **Condizione di Entrata in Copertura:** Si apre una posizione short (per coprire una parte del portafoglio) quando la media mobile veloce incrocia al ribasso quella lenta E l'indicatore ADX è superiore a una certa soglia, a conferma che è presente un trend definito.\n- **Condizione di Uscita dalla Copertura:** La copertura viene chiusa quando il segnale degli indicatori cessa o quando scatta lo stop loss.\n- **Stop Loss:** Una misura di sicurezza chiude la copertura se il prezzo sale di una certa percentuale, limitando le perdite sulla singola operazione di hedging.")
    st.subheader("Parametri Ottimali Utilizzati"); st.markdown("I seguenti parametri sono stati 'bloccati' dopo la Fase 2 di ottimizzazione e sono usati come default dall'applicazione:"); st.code(f"OPTIMAL_PARAMS = {OPTIMAL_PARAMS}", language="python")

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
    stop_loss_perc_backtest = st.sidebar.slider("Stop Loss sulle Coperture (%)", 0, 50, 0, help="Impostare a 0 per disattivare lo stop loss.") / 100.0
    run_backtest_button = st.sidebar.button("Esegui Backtest", type="primary")
    render_historical_backtest_tab(ticker_backtest, start_date_backtest, initial_capital_backtest, hedge_ratio_backtest, stop_loss_perc_backtest, run_backtest_button)

elif active_tab == "Metodologia":
    render_methodology_tab()

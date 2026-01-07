# btc_bot_runner.py
# VERSIONE CORRETTA: Include simulazione storica per coerenza con Backtest e Stop Loss

import configparser
from datetime import datetime, timedelta
import pandas as pd

# Import moduli locali
from data_handler import EODHDClient
from indicator_calculator import IndicatorCalculator
from telegram_notifier import send_telegram_message

def generate_btc_signal():
    print("Avvio processo di generazione segnale BTC (Logic-Consistent)...")
    
    # 1. Carica la configurazione
    config = configparser.ConfigParser()
    config.read('config.ini')

    api_key = config.get('EODHD', 'api_key')
    bot_token = config.get('TELEGRAM', 'bot_token')
    chat_id = config.get('TELEGRAM', 'chat_id')
    
    # Parametri Strategia
    ticker = config.get('STRATEGY', 'ticker')
    fast_ma = config.getint('STRATEGY', 'fast_ma')
    slow_ma = config.getint('STRATEGY', 'slow_ma')
    adx_period = config.getint('STRATEGY', 'adx_period')
    adx_threshold = config.getfloat('STRATEGY', 'adx_threshold')
    
    # Parametro Stop Loss (Default 3% se non presente nel config)
    if config.has_option('STRATEGY', 'stop_loss_perc'):
        stop_loss_perc = config.getfloat('STRATEGY', 'stop_loss_perc')
    else:
        stop_loss_perc = 0.03 # Default cautelativo

    # 2. Scarica dati (Storico sufficiente per stabilizzare indicatori e simulare trade recenti)
    print(f"Recupero dati per {ticker}...")
    try:
        client = EODHDClient()
        # Prendiamo 500 giorni per sicurezza sulle medie mobili lunghe
        start_date = (datetime.now() - timedelta(days=500)).strftime('%Y-%m-%d')
        data_df = client.get_historical_data(api_key, ticker, start_date)
        if data_df is None or data_df.empty:
            raise ValueError("Dati scaricati vuoti.")
    except Exception as e:
        error_msg = f"ERRORE CRITICO {ticker}: {e}"
        print(error_msg)
        send_telegram_message(error_msg, bot_token, chat_id)
        return

    # 3. Calcola indicatori
    print("Calcolo indicatori...")
    calc = IndicatorCalculator()
    data_df = calc.add_moving_average(data_df, period=fast_ma)
    data_df = calc.add_moving_average(data_df, period=slow_ma)
    data_df = calc.add_adx(data_df, period=adx_period)
    data_df.dropna(inplace=True)

    # 4. SIMULAZIONE STATO REALE (Core Logic Fix)
    # Ripercorriamo la storia per vedere se siamo DENTRO o FUORI (causa Stop Loss)
    print("Esecuzione simulazione storica per determinare lo stato reale...")
    
    in_position = False
    entry_price = 0.0
    exit_reason = ""
    
    # Creiamo una serie booleana per efficienza
    signal_condition_series = (data_df[f"sma_{fast_ma}"] < data_df[f"sma_{slow_ma}"]) & \
                              (data_df[f"ADX_{adx_period}"] > adx_threshold)

    # Iteriamo su tutto il dataframe
    for i in range(len(data_df)):
        current_price = data_df['adj_close'].iloc[i]
        is_signal = signal_condition_series.iloc[i]

        if is_signal and not in_position:
            # Condizione di ENTRATA
            in_position = True
            entry_price = current_price
            exit_reason = ""
        
        elif in_position:
            # Condizione 1: STOP LOSS
            if current_price > entry_price * (1 + stop_loss_perc):
                in_position = False
                exit_reason = "Stop Loss Scattato"
            
            # Condizione 2: FINE SEGNALE (Medie incrociano o ADX cala)
            elif not is_signal:
                in_position = False
                exit_reason = "Segnale Terminato"

    # 5. Formatta e invia messaggio in base allo stato FINALE
    last_row = data_df.iloc[-1]
    current_date = last_row.name.strftime('%Y-%m-%d')
    current_close = last_row['adj_close']
    
    # Determinazione icone e testo
    if in_position:
        status_header = "🟢 COPERTURA ATTIVA"
        # Calcolo P&L teorico della copertura (siamo short, quindi entry - current)
        pnl_perc = ((entry_price - current_close) / entry_price) * 100
        pnl_icon = "📈" if pnl_perc > 0 else "📉"
        
        detail_text = (
            f"Prezzo Entry: ${entry_price:,.2f}\n"
            f"Prezzo Attuale: ${current_close:,.2f}\n"
            f"P&L Copertura: {pnl_icon} {pnl_perc:.2f}%"
        )
    else:
        status_header = "🔴 NESSUNA COPERTURA"
        if exit_reason:
            detail_text = f"Motivo: {exit_reason}"
        else:
            detail_text = "Nessun segnale di trend ribassista rilevato."

    message = (
        f"**Kriterion Hedging Bot - {ticker}** 🛡️\n\n"
        f"📅 Data: {current_date}\n"
        f"📊 Stato: **{status_header}**\n\n"
        f"{detail_text}\n\n"
        f"⚙️ _ADX: {last_row[f'ADX_{adx_period}']:.1f} | SL: {stop_loss_perc*100}%_"
    )
    
    print("\n--- Invio Notifica Telegram ---")
    print(message)
    send_telegram_message(message, bot_token, chat_id)

if __name__ == '__main__':
    generate_btc_signal()

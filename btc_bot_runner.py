# btc_bot_runner.py

import configparser
from datetime import datetime, timedelta

# Ora tutti i moduli vengono importati direttamente perché sono nella stessa cartella
from data_handler import EODHDClient
from indicator_calculator import IndicatorCalculator
from telegram_notifier import send_telegram_message

def generate_btc_signal():
    print("Avvio processo di generazione segnale BTC...")
    
    # 1. Carica la configurazione
    config = configparser.ConfigParser()
    config.read('config.ini')

    # Recupera credenziali e parametri
    api_key = config.get('EODHD', 'api_key')
    bot_token = config.get('TELEGRAM', 'bot_token')
    chat_id = config.get('TELEGRAM', 'chat_id')
    ticker = config.get('STRATEGY', 'ticker')
    fast_ma = config.getint('STRATEGY', 'fast_ma')
    slow_ma = config.getint('STRATEGY', 'slow_ma')
    adx_period = config.getint('STRATEGY', 'adx_period')
    adx_threshold = config.getfloat('STRATEGY', 'adx_threshold')
    
    # 2. Scarica dati
    print(f"Recupero dati per {ticker}...")
    try:
        client = EODHDClient()
        start_date = (datetime.now() - timedelta(days=500)).strftime('%Y-%m-%d')
        data_df = client.get_historical_data(api_key, ticker, start_date)
        if data_df is None or data_df.empty:
            raise ValueError("I dati scaricati sono vuoti.")
    except Exception as e:
        error_msg = f"ERRORE CRITICO: Impossibile scaricare i dati per {ticker}. Dettagli: {e}"
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

    # 4. Estrai segnale
    print("Estraendo l'ultimo segnale...")
    last_row = data_df.iloc[-1]
    signal_active = (last_row[f"sma_{fast_ma}"] < last_row[f"sma_{slow_ma}"]) and \
                    (last_row[f"ADX_{adx_period}"] > adx_threshold)

    # 5. Formatta e invia messaggio
    current_date = last_row.name.strftime('%Y-%m-%d')
    status_text = "🟢 ATTIVA" if signal_active else "🔴 NON ATTIVA"
    message = (
        f"**Segnale di Copertura Kriterion - {ticker}** 🛡️\n\n"
        f"*- Data Riferimento:* {current_date}\n"
        f"*- Stato Attuale:* **{status_text}**"
    )
    
    print("\n--- Invio Notifica Telegram ---")
    print(message)
    send_telegram_message(message, bot_token, chat_id)
    print("Processo completato.")

if __name__ == '__main__':
    generate_btc_signal()

# File: data_handler.py
# Modulo per il progetto KriterionQuant Hedging App

import pandas as pd
import requests
import time
from datetime import datetime

class EODHDClient:
    """
    Gestisce tutte le comunicazioni con l'API EODHD per il recupero
    dei dati storici.
    """
    BASE_URL = "https://eodhd.com/api/eod/"

    def get_historical_data(self, api_key: str, ticker: str, start_date: str) -> pd.DataFrame | None:
        """
        Recupera i dati storici giornalieri per un dato ticker.

        Args:
            api_key (str): La tua chiave API per EODHD.
            ticker (str): Il ticker da scaricare (es. 'BTC-USD.CC').
            start_date (str): La data di inizio in formato 'YYYY-MM-DD'.

        Returns:
            pd.DataFrame | None: Un DataFrame pandas con dati OHLCV o None in caso di errore.
        """
        endpoint = f"{self.BASE_URL}{ticker}"
        end_date = datetime.now().strftime('%Y-%m-%d')
        
        params = {
            "api_token": api_key,
            "from": start_date,
            "to": end_date,
            "period": "d",
            "fmt": "json"
        }
        
        # Includere un leggero ritardo per rispettare i rate limit dell'API
        time.sleep(0.5)

        try:
            response = requests.get(endpoint, params=params)
            # Solleva un'eccezione per errori HTTP (es. 401, 403, 404, 429)
            response.raise_for_status()
            
            data = response.json()
            if not isinstance(data, list) or not data:
                print(f"Nessun dato o formato inatteso per {ticker}.")
                return None
            
            df = pd.DataFrame(data)
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            df.rename(columns={'adjusted_close': 'adj_close'}, inplace=True)
            
            # Assicuriamoci che le colonne numeriche siano del tipo corretto
            ohlcv_cols = ['open', 'high', 'low', 'close', 'adj_close', 'volume']
            for col in ohlcv_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            print(f"Dati per {ticker} scaricati con successo: {len(df)} righe.")
            return df[ohlcv_cols]

        except requests.exceptions.RequestException as e:
            print(f"Errore durante la richiesta API: {e}")
            return None
        except Exception as e:
            print(f"Errore imprevisto nella gestione dei dati per {ticker}: {e}")
            return None

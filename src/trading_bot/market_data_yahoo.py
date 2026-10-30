import logging
import pandas as pd
import yfinance as yf

# Silence les logs HTTP/yfinance verbeux qui polluent le terminal
logging.getLogger("yfinance").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)

class YahooMarketData:
    """Fournisseur de données de marché gratuit basé sur Yahoo Finance."""

    @staticmethod
    def get_live_price(symbol: str) -> dict:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.fast_info
            
            last_price = info.get('lastPrice') or info.get('previousClose')
            
            data = {
                'symbol': symbol,
                'last': round(last_price, 2) if last_price else None,
                'previous_close': round(info.get('previousClose', 0.0), 2),
                'currency': info.get('currency', 'USD')
            }
            
            logging.info(f" [YAHOO] {symbol} | Dernier prix : {data['last']} {data['currency']}")
            return data
        except Exception as e:
            logging.warning(f" Impossible de récupérer le prix direct pour {symbol}: {e}")
            return {'symbol': symbol, 'last': None, 'previous_close': None, 'currency': 'USD'}

    @staticmethod
    def get_historical_candles(
        symbol: str, 
        period: str = "5d", 
        interval: str = "5m"
    ) -> pd.DataFrame:
        """
        Récupère les bougies historiques (OHLCV).
        """
        logging.info(f" Récupération historique Yahoo pour {symbol} (Période: {period}, Intervalle: {interval})...")
        
        try:
            ticker = yf.Ticker(symbol)
            # progress=False évite l'affichage de barres de chargement intempestives
            df = ticker.history(period=period, interval=interval)
            
            if df is None or df.empty:
                logging.warning(f" Aucune donnée trouvée pour {symbol}.")
                return pd.DataFrame()

            # Nettoyage et harmonisation du DataFrame
            df.columns = [col.lower() for col in df.columns]
            df = df[['open', 'high', 'low', 'close', 'volume']]
            
            # Formatage des prix
            for col in ['open', 'high', 'low', 'close']:
                df[col] = df[col].round(2)

            logging.info(f" {len(df)} bougies récupérées avec succès.")
            return df
        except Exception as e:
            logging.error(f" Erreur lors de la récupération des bougies pour {symbol}: {e}")
            return pd.DataFrame()
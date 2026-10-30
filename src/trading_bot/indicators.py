import pandas as pd
import numpy as np
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class TechnicalIndicators:
    """Calculateur d'indicateurs techniques natif Pandas (sans dépendances externes lourdes)."""

    @staticmethod
    def add_sma(df: pd.DataFrame, window: int = 20, column: str = 'close') -> pd.DataFrame:
        """Ajoute une Moyenne Mobile Simple (SMA)."""
        df[f'sma_{window}'] = df[column].rolling(window=window).mean().round(2)
        return df

    @staticmethod
    def add_ema(df: pd.DataFrame, window: int = 20, column: str = 'close') -> pd.DataFrame:
        """Ajoute une Moyenne Mobile Exponentielle (EMA)."""
        df[f'ema_{window}'] = df[column].ewm(span=window, adjust=False).mean().round(2)
        return df

    @staticmethod
    def add_rsi(df: pd.DataFrame, window: int = 14, column: str = 'close') -> pd.DataFrame:
        """Ajoute l'indice de force relative (RSI)."""
        delta = df[column].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()

        rs = gain / loss
        df[f'rsi_{window}'] = (100 - (100 / (1 + rs))).round(2)
        return df

    @classmethod
    def generate_signals(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcule un jeu d'indicateurs et génère un signal de trading basique :
        - BUY  : SMA 20 croise au-dessus de SMA 50 ET RSI < 70
        - SELL : SMA 20 croise en-dessous de SMA 50 OU RSI > 70
        - HOLD : Pas de signal particulier
        """
        if df.empty or len(df) < 50:
            logging.warning("Pas assez de données pour calculer les indicateurs (50 bougies min).")
            return df

        # Calcul des indicateurs
        df = cls.add_sma(df, window=20)
        df = cls.add_sma(df, window=50)
        df = cls.add_rsi(df, window=14)

        # Génération des signaux
        df['signal'] = 'HOLD'
        
        # Conditions d'achat / vente
        buy_cond = (df['sma_20'] > df['sma_50']) & (df['rsi_14'] < 70)
        sell_cond = (df['sma_20'] < df['sma_50']) | (df['rsi_14'] > 70)

        df.loc[buy_cond, 'signal'] = 'BUY'
        df.loc[sell_cond, 'signal'] = 'SELL'

        return df
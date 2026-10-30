from market_data_yahoo import YahooMarketData
from indicators import TechnicalIndicators

def main():
    print("=== TEST MODULE INDICATEURS & SIGNAUX ===\n")
    
    # 1. Récupération de l'historique Yahoo (ex: AAPL, 1 mois de bougies 1 heure)
    symbol = "AAPL"
    print(f"1. Récupération des données pour {symbol}...")
    df = YahooMarketData.get_historical_candles(symbol, period="1mo", interval="1h")
    
    if df.empty:
        print("Erreur : Impossible de récupérer les données.")
        return

    # 2. Calcul des indicateurs et génération des signaux
    print("\n2. Calcul des indicateurs (SMA 20, SMA 50, RSI 14)...")
    df_signals = TechnicalIndicators.generate_signals(df)

    # 3. Affichage des dernières bougies avec le signal
    print("\n3. Aperçu des 10 dernières bougies avec signaux :")
    cols_to_show = ['close', 'sma_20', 'sma_50', 'rsi_14', 'signal']
    print(df_signals[cols_to_show].tail(10))

    # 4. Résumé du dernier signal connu
    last_row = df_signals.iloc[-1]
    print(f"\n--- DERNIER SIGNAL POUR {symbol} ---")
    print(f"Prix de clôture : {last_row['close']} USD")
    print(f"SMA 20 : {last_row['sma_20']} | SMA 50 : {last_row['sma_50']}")
    print(f"RSI 14 : {last_row['rsi_14']}")
    print(f"SIGNAL ACTUEL : [{last_row['signal']}]")

if __name__ == "__main__":
    main()
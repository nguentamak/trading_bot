from market_data_yahoo import YahooMarketData

def main():
    print("=== TEST MODULE MARCHÉ (YAHOO FINANCE) ===\n")
    
    # 1. Test prix instantané (ex. Apple et S&P 500)
    apple_price = YahooMarketData.get_live_price("AAPL")
    sp500_price = YahooMarketData.get_live_price("^GSPC")
    
    # 2. Test bougies historiques 5 minutes sur 5 jours
    print("\n--- Récupération des bougies 5 min pour AAPL ---")
    df_candles = YahooMarketData.get_historical_candles(
        symbol="AAPL", 
        period="5d", 
        interval="5m"
    )
    
    if not df_candles.empty:
        print("\nAperçu des 5 dernières bougies :")
        print(df_candles.tail(5))

if __name__ == "__main__":
    main()
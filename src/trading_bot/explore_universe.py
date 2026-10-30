from market_data_yahoo import YahooMarketData

# Panier d'actifs internationaux
ASSETS = {
    "US Tech": "AAPL",
    "CAC 40 (France)": "MC.PA",
    "DAX (Allemagne)": "SAP.DE",
    "Nikkei (Japon)": "7203.T",
    "Forex (EUR/USD)": "EURUSD=X",
    "Or (Gold)": "GC=F",
    "Bitcoin": "BTC-USD"
}

def main():
    print("=== EXPLORATION DES MARCHÉS PAR CONTINENT / CLASSE D'ACTIFS ===\n")
    
    for category, ticker in ASSETS.items():
        data = YahooMarketData.get_live_price(ticker)
        price = data.get('last')
        currency = data.get('currency', '')
        print(f"• {category:20} | Ticker: {ticker:10} | Prix : {price} {currency}")

if __name__ == "__main__":
    main()
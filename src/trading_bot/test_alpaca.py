import logging
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import MarketOrderRequest, TakeProfitRequest, StopLossRequest

# 1. Renseignez vos clés Paper Trading
API_KEY = "PKVAPM3RKIWFX2NLKN7GO4BHXQ"
SECRET_KEY = "GJEh9f1anYwj6VuXoSUmjUBpYsjuW7MQTJ8eXuc3jdGt"

# Initialisation du client Alpaca en mode Paper Trading
client = TradingClient(API_KEY, SECRET_KEY, paper=True)

def tester_passage_ordre():
    # 2. Vérification du compte
    account = client.get_account()
    print("=== INFO COMPTE PAPER TRADING ===")
    print(f"Solde virtuel disponible (Equity) : {account.equity} $")
    print(f"Pouvoir d'achat (Buying Power)    : {account.buying_power} $\n")

    # 3. Préparation d'un ordre d'achat sur Apple (AAPL)
    # Exemple : Achat de 1 action avec Stop-Loss à 210$ et Take-Profit à 230$
    symbol = "AAPL"
    
    req = MarketOrderRequest(
        symbol=symbol,
        qty=1,
        side=OrderSide.BUY,
        time_in_force=TimeInForce.GTC,
        take_profit=TakeProfitRequest(limit_price=230.0),
        stop_loss=StopLossRequest(stop_price=210.0),
    )

    try:
        order = client.submit_order(order_data=req)
        print(f"✅ Ordre Bracket envoyé sur {symbol} !")
        print(f"   ID Ordre : {order.id}")
        print(f"   Statut   : {order.status}\n")
    except Exception as e:
        print(f"❌ Erreur lors de l'envoi : {e}\n")

    # 4. Affichage des positions ouvertes
    positions = client.get_all_positions()
    print("=== POSITIONS ACTIVES ===")
    for pos in positions:
        print(f"Ticker: {pos.symbol} | Quantité: {pos.qty} | Prix moyen: {pos.avg_entry_price} $")

if __name__ == "__main__":
    tester_passage_ordre()
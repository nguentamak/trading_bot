import os
import requests
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetPortfolioHistoryRequest
from alpaca.trading.enums import TimeFrame

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Initialisation du client Alpaca (récupère automatiquement les clés depuis l'environnement)
IS_PAPER = os.getenv("ALPACA_PAPER", "True").lower() == "true"
trading_client = TradingClient(
    api_key=os.getenv("ALPACA_API_KEY"),
    secret_key=os.getenv("ALPACA_SECRET_KEY"),
    paper=IS_PAPER
)

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            print(f"❌ Erreur envoi Telegram hebdo : {response.text}")
        else:
            print("✅ Récapitulatif hebdomadaire envoyé avec succès !")
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Avertissement : Impossible d'envoyer la notification Telegram (Problème réseau/DNS) : {e}")

def get_alpaca_weekly_profit():
    """Récupère le profit/perte net(te) de la semaine via l'historique du portefeuille Alpaca."""
    try:
        params = GetPortfolioHistoryRequest(
            period="1W",
            timeframe=TimeFrame.Day,
            extended_hours=True
        )
        history = trading_client.get_portfolio_history(params)
        
        if history.profit_loss and len(history.profit_loss) > 0:
            weekly_profit = float(history.profit_loss[-1])
            return weekly_profit
        return 0.0
    except Exception as e:
        print(f"⚠️ Erreur lors de la récupération des données Alpaca : {e}")
        return 0.0

def calculate_weekly_skimming():
    weekly_profit = get_alpaca_weekly_profit()
    
    if weekly_profit <= 0:
        message = (
            f"📊 *Bilan Hebdomadaire - Stratégie de Skimming*\n\n"
            f"📉 Profit net de la semaine : *{weekly_profit:.2f} $*\n\n"
            f"Aucun profit à écrêter cette semaine. Capital préservé pour le prochain cycle !"
        )
        send_telegram_message(message)
        return

    transfer_to_pea = weekly_profit * 0.50
    reinvest_trading = weekly_profit * 0.50

    message = (
        f"📊 *Bilan Hebdomadaire - Stratégie de Skimming*\n\n"
        f"💰 Profit net de la semaine : *+{weekly_profit:.2f} $*\n\n"
        f"🎯 *Allocation des profits (50/50) :*\n"
        f"🏦 À transférer vers le PEA (ETF) : *+{transfer_to_pea:.2f} $*\n"
        f"♻️ Réinvesti en capital de trading : *+{reinvest_trading:.2f} $*\n\n"
        f"_Pense à effectuer ton virement manuel vers ton PEA pour acheter tes parts d'ETF !_"
    )
    
    send_telegram_message(message)

if __name__ == "__main__":
    calculate_weekly_skimming()
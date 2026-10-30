import os
import requests
# Importe ici tes modules Alpaca selon ta structure existante (ex: alpaca_trade_api ou alpaca-py)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    
    try:
        # Ajout d'un timeout de 10 secondes et protection contre les pannes réseau/DNS
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            print(f"❌ Erreur envoi Telegram hebdo : {response.text}")
        else:
            print("✅ Récapitulatif hebdomadaire envoyé avec succès !")
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Avertissement : Impossible d'envoyer la notification Telegram (Problème réseau/DNS) : {e}")

def calculate_weekly_skimming():
    # --- LOGIQUE FINANCIÈRE ---
    # 1. Récupérer le solde ou les profits réalisés de la semaine via l'API Alpaca
    weekly_profit = 240.00  # Exemple : 240 € de bénéfices nets cette semaine
    
    # 2. Appliquer la règle des 50% pour le PEA (ETF MSCI World / S&P 500)
    transfer_to_pea = weekly_profit * 0.50
    reinvest_trading = weekly_profit * 0.50

    # --- CONSTRUCTION DU MESSAGE ---
    message = (
        f"📊 *Bilan Hebdomadaire - Stratégie de Skimming*\n\n"
        f"💰 Profit net de la semaine : *+{weekly_profit:.2f} €*\n\n"
        f"🎯 *Allocation des profits (50/50) :*\n"
        f"🏦 À transférer vers le PEA (ETF) : *+{transfer_to_pea:.2f} €*\n"
        f"♻️ Réinvesti en capital de trading : *+{reinvest_trading:.2f} €*\n\n"
        f"_Pense à effectuer ton virement manuel vers ton PEA pour acheter tes parts d'ETF !_"
    )
    
    send_telegram_message(message)

if __name__ == "__main__":
    calculate_weekly_skimming()
import os
import csv
import requests
import logging

# ==========================================
# CONFIGURATION DES LOGS HORODATÉS
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler()
    ]
)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Récupération et découpage des différents Chat IDs séparés par des virgules
TELEGRAM_CHAT_IDS_ENV = os.getenv("TELEGRAM_CHAT_ID", "")
CHAT_IDS = [chat_id.strip() for chat_id in TELEGRAM_CHAT_IDS_ENV.split(",") if chat_id.strip()]

def send_telegram_message(text):
    """Envoie un message via l'API Telegram à tous les destinataires configurés"""
    if not TELEGRAM_BOT_TOKEN:
        logging.error("❌ TELEGRAM_BOT_TOKEN manquant dans l'environnement !")
        return
    
    if not CHAT_IDS:
        logging.error("❌ Aucun TELEGRAM_CHAT_ID configuré !")
        return

    for chat_id in CHAT_IDS:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown", "disable_web_page_preview": True}
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code != 200:
                logging.error(f"❌ Échec envoi Telegram pour {chat_id} : {response.text}")
            else:
                logging.info(f"✅ Notification Telegram envoyée avec succès à {chat_id} !")
        except Exception as e:
            logging.error(f"❌ Erreur réseau Telegram pour {chat_id} : {e}")

def notify_top_setups():
    """Lit le fichier CSV et envoie les résultats sur Telegram en tronçonnant si le message est trop long"""
    csv_filename = "scanner_results.csv"
    
    if not os.path.exists(csv_filename):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        csv_filename = os.path.join(base_dir, "scanner_results.csv")
        
    if not os.path.exists(csv_filename):
        logging.info("⚠️ Aucun fichier 'scanner_results.csv' trouvé. Pas de notification envoyée.")
        return

    setups = []
    try:
        with open(csv_filename, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                setups.append(row)
    except Exception as e:
        logging.error(f"❌ Erreur lecture CSV : {e}")
        return

    if not setups:
        logging.info("⚠️ Le fichier CSV est vide. Pas d'alerte à envoyer.")
        return

    # Construction dynamique avec gestion de la limite des 4096 caractères
    header = f"🚨 *Rapport Swing Trading - {len(setups)} Opportunité(s) du jour* 🚨\n\n"
    current_message = header

    for s in setups:
        ticker = s.get('Ticker', 'N/A')
        yahoo_link = f"https://finance.yahoo.com/quote/{ticker}"
        
        setup_text = (
            f"🔹 *[{s.get('Category', 'Marché')}] [{ticker}]({yahoo_link})*\n"
            f"  • Signal : _{s.get('Signal', 'N/A')}_\n"
            f"  • Score de Conviction : *{s.get('Conviction_Score', 'N/A')}/100*\n"
            f"  • Prix : {s.get('Price', 'N/A')} | RSI : {s.get('RSI', 'N/A')}\n"
            f"  • Ratios -> Sortino: {s.get('Sortino', 'N/A')} | Calmar: {s.get('Calmar', 'N/A')} | Max DD: {s.get('Max_Drawdown_pct', 'N/A')}%\n"
            f"  • 🛡️ Stop-Loss (1.5x ATR) : *{s.get('SL_1.5xATR', 'N/A')}*\n"
            f"  • 🎯 Take-Profit (3.0x ATR) : *{s.get('TP_3.0xATR', 'N/A')}*\n\n"
        )

        # Si ajouter ce setup dépasse ~3800 caractères, on envoie le paquet actuel et on recommence
        if len(current_message) + len(setup_text) > 3800:
            send_telegram_message(current_message)
            current_message = "🚨 *Rapport Swing Trading (suite)* 🚨\n\n" + setup_text
        else:
            current_message += setup_text

    # Envoi du dernier bloc de messages
    if len(current_message) > len(header):
        send_telegram_message(current_message)

if __name__ == "__main__":
    notify_top_setups()
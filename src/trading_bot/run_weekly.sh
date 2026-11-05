#!/bin/bash

# 1. Variables Telegram
export TELEGRAM_BOT_TOKEN="8405354536:AAHRG8LWXRMntv_FTlhafzeZ_888HzgvkV8"
export TELEGRAM_CHAT_ID="8701571717"  # Remplace par ton vrai Chat ID complet

# 2. Utilisation directe du Python de l'environnement virtuel (plus fiable pour cron)
# Remplace par le chemin exact retourné par la commande 'which python'
VENV_PYTHON="/home/sergengue/trading_bot/.venv/bin/python"

# 3. Lancer les scripts avec le python de l'environnement
echo "--- Lancement du bilan hebdomadaire PEA à $(date) ---" >> bot.log
# $VENV_PYTHON /home/sergengue/trading_bot/src/trading_bot/weekly_summary.py >> /home/sergengue/trading_bot/src/trading_bot/bot.log 2>&1
python weekly_summary.py >> bot.log 2>&1
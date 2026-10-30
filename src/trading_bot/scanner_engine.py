import yfinance as yf
import pandas as pd
import numpy as np
import requests
import csv
import os
import logging
from datetime import datetime

# ==========================================
# CONFIGURATION DES LOGS HORODATÉS
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler() # Affiche dans la console (capturé par run_bot.sh dans bot.log)
    ]
)

# ==========================================
# 1. GENERATION DYNAMIQUE DE L'UNIVERS
# ==========================================

def get_dynamic_sp500():
    """Récupère la liste actualisée du S&P 500 depuis une source CSV brute ultra-stable"""
    try:
        url = 'https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv'
        df = pd.read_csv(url)
        tickers = df['Symbol'].tolist()
        tickers = [t.replace('.', '-') for t in tickers]
        logging.info(f"🌐 S&P 500 chargé dynamiquement : {len(tickers)} actions.")
        return tickers
    except Exception as e:
        logging.warning(f"⚠️ Erreur chargement dynamique S&P 500, fallback actif : {e}")
        return ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AMD"]

def get_dynamic_cac40():
    """Fournit la liste officielle et actualisée des constituants du CAC 40 adaptés à yfinance"""
    cac40_tickers = [
        "AC.PA", "AI.PA", "AIR.PA", "MT", "ATO.PA", "BN.PA", "BNP.PA", "EN.PA", 
        "CA.PA", "CAP.PA", "GTT.PA", "DSY.PA", "ENGI.PA", "EL.PA", "ERF.PA", "RMS.PA", 
        "KER.PA", "OR.PA", "LR.PA", "MC.PA", "ML.PA", "ORA.PA", "RI.PA", "PUB.PA", 
        "RNO.PA", "SAF.PA", "SGO.PA", "SAN.PA", "SU.PA", "GLE.PA", "STLAM.MI", "STM.MI", 
        "TEP.PA", "TTE.PA", "URW.PA", "VIE.PA", "DG.PA", "VIV.PA", "WLN.PA"
    ]
    logging.info(f"🇫🇷 CAC 40 chargé (Référence officielle) : {len(cac40_tickers)} actions.")
    return cac40_tickers

def get_dynamic_top_crypto(limit=25):
    """Récupère les top cryptos filtrées et adaptées à Yahoo Finance"""
    try:
        url = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=volume_desc&per_page={limit}&page=1"
        response = requests.get(url, timeout=5)
        data = response.json()
        
        valid_crypto_symbols = {"BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "AVAX", "LINK", "DOGE", "DOT"}
        
        tickers = []
        for coin in data:
            sym = coin['symbol'].upper()
            if sym in valid_crypto_symbols:
                tickers.append(f"{sym}-USD")
                
        fallback_cryptos = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD"]
        for fc in fallback_cryptos:
            if fc not in tickers:
                tickers.append(fc)
                
        logging.info(f"🌐 Top Cryptos validées pour Yahoo Finance : {len(tickers)} actifs.")
        return tickers
    except Exception as e:
        logging.warning(f"⚠️ Erreur chargement cryptos, fallback actif : {e}")
        return ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD"]

def build_market_universe():
    """Assemble l'univers actif (restreint temporairement au S&P 500)"""
    return {
        "US_Large_Caps": get_dynamic_sp500()
        
        # --- MARCHÉS MOMENTANÉMENT DÉSACTIVÉS ---
        # "Crypto": get_dynamic_top_crypto(limit=15),
        # "Indices_Majeurs": ["^GSPC", "^IXIC", "^DJI", "^STOXX50E", "^FCHI", "^N225"],
        # "Forex": ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X"],
        # "CAC_40": get_dynamic_cac40(),
    }

# ==========================================
# 2. FONCTIONS DE CALCUL ET FILTRAGE
# ==========================================

def fetch_data(ticker, period="1y"):
    """Télécharge l'historique daily du ticker via yfinance en mode silencieux"""
    df = yf.download(ticker, period=period, progress=False, auto_adjust=True)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

def calculate_risk_metrics(df, risk_free_rate=0.03):
    """Calcule Sortino, Calmar, Max Drawdown et ATR"""
    close = df['Close']
    returns = close.pct_change().dropna()
    
    if len(returns) < 50:
        return None

    cum_returns = (1 + returns).cumprod()
    peak = cum_returns.cummax()
    drawdown = (cum_returns - peak) / peak
    max_drawdown = drawdown.min()

    trading_days = 252
    mean_return = returns.mean() * trading_days
    downside_returns = returns[returns < 0]
    downside_std = downside_returns.std() * np.sqrt(trading_days)
    sortino = (mean_return - risk_free_rate) / downside_std if downside_std > 0 else 0.0

    annual_return = (close.iloc[-1] / close.iloc[0]) ** (trading_days / len(close)) - 1
    calmar = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0.0

    high = df['High']
    low = df['Low']
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=14).mean().iloc[-1]

    return {
        "Sortino": round(float(sortino), 2),
        "Calmar": round(float(calmar), 2),
        "Max_Drawdown_pct": round(float(max_drawdown * 100), 2),
        "ATR": round(float(atr), 2)
    }

def apply_filters(df, category):
    """Applique les filtres de liquidité, tendance, momentum et génère le signal"""
    if df.empty or len(df) < 200:
        return None, "Données insuffisantes"

    close = df['Close']
    volume = df['Volume']
    high = df['High']

    avg_volume_20 = volume.rolling(window=20).mean().iloc[-1]
    if category in ["US_Large_Caps", "Crypto", "CAC_40"] and avg_volume_20 < 3_000_000:
        return None, "Liquidité insuffisante (< 3M)"

    sma_50 = close.rolling(window=50).mean().iloc[-1]
    sma_200 = close.rolling(window=200).mean().iloc[-1]
    last_price = close.iloc[-1]

    is_uptrend = (last_price > sma_50) and (last_price > sma_200) and (sma_50 > sma_200)
    if not is_uptrend:
        return None, "Hors tendance haussière"

    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    last_rsi = rsi.iloc[-1]

    high_3d = high.iloc[-4:-1].max()
    is_breakout_3d = last_price > high_3d

    has_momentum = (55 <= last_rsi <= 65) and is_breakout_3d
    if not has_momentum:
        return None, "Pas de setup momentum strict (RSI 55-65)"

    risk_metrics = calculate_risk_metrics(df)
    if not risk_metrics:
        return None, "Erreur calcul métriques"

    conviction_score = 50
    if risk_metrics["Sortino"] > 1.5: conviction_score += 15
    if risk_metrics["Calmar"] > 1.0: conviction_score += 15
    if risk_metrics["Max_Drawdown_pct"] > -15: conviction_score += 10
    if 58 <= last_rsi <= 62: conviction_score += 10

    # NOUVEAU : Exiger un score élite de 75 minimum
    if conviction_score < 75:
        return None, f"Score de conviction insuffisant ({conviction_score}/100)"

    atr = risk_metrics["ATR"]
    sl = last_price - (1.5 * atr)
    tp = last_price + (3.0 * atr)

    signal_type = "BUY - Breakout 3J & Momentum"

    return {
        "Price": round(float(last_price), 2),
        "RSI": round(float(last_rsi), 1),
        "Signal": signal_type,
        "Conviction_Score": conviction_score,
        "Sortino": risk_metrics["Sortino"],
        "Calmar": risk_metrics["Calmar"],
        "Max_Drawdown_pct": risk_metrics["Max_Drawdown_pct"],
        "ATR": atr,
        "SL_1.5xATR": round(sl, 2),
        "TP_3.0xATR": round(tp, 2),
        "Volume_M_20d": int(avg_volume_20) if category in ["US_Large_Caps", "Crypto", "CAC_40"] else "N/A"
    }, "OK"

# ==========================================
# 3. EXPORT CSV ET EXECUTION PRINCIPALE
# ==========================================

def save_results_to_csv(results, filename="scanner_results.csv"):
    """Exporte les résultats du scanner dans un fichier CSV avec la colonne Signal"""
    if not results:
        logging.warning("⚠️ Aucun résultat à exporter dans le CSV.")
        return

    fields = ["Ticker", "Category", "Price", "RSI", "Signal", "Conviction_Score", "Sortino", "Calmar", "Max_Drawdown_pct", "SL_1.5xATR", "TP_3.0xATR"]
    
    try:
        filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(fields)
            for ticker, data in results.items():
                row = [
                    ticker, data["Category"], data["Price"], data["RSI"], data["Signal"],
                    data["Conviction_Score"], data["Sortino"], data["Calmar"], 
                    data["Max_Drawdown_pct"], data["SL_1.5xATR"], data["TP_3.0xATR"]
                ]
                writer.writerow(row)
        logging.info(f"📁 Résultats exportés avec succès dans : {filepath}")
    except Exception as e:
        logging.error(f"❌ Erreur lors de l'export CSV : {e}")

def run_screener():
    selected_setups = {}
    universe = build_market_universe()

    for category, tickers in universe.items():
        logging.info(f"🔍 Analyse de la catégorie : {category} ({len(tickers)} actifs)...")
        for ticker in tickers:
            try:
                df = fetch_data(ticker)
                if df is None or df.empty:
                    continue
                metrics, status = apply_filters(df, category)
                if status == "OK":
                    selected_setups[ticker] = {
                        "Category": category,
                        **metrics
                    }
            except Exception:
                continue

    return selected_setups

if __name__ == "__main__":
    logging.info("🚀 Démarrage du scan multi-actifs dynamique (US, CAC 40, Crypto, Forex)...")
    results = run_screener()
    
    if not results:
        logging.info("❌ Aucune opportunité ne valide 100% des critères ce soir.")
    else:
        logging.info(f"\n✅ {len(results)} opportunité(s) sélectionnée(s) :")
        for ticker, data in results.items():
            logging.info(f"\n[{data['Category']}] {ticker} ({data['Signal']} | Score: {data['Conviction_Score']}/100)")
            logging.info(f"  Prix: {data['Price']} | RSI: {data['RSI']}")
            logging.info(f"  Sortino: {data['Sortino']} | Calmar: {data['Calmar']} | Max DD: {data['Max_Drawdown_pct']}%")
            logging.info(f"  SL (1.5x ATR): {data['SL_1.5xATR']} | TP (3x ATR): {data['TP_3.0xATR']}")
        
        save_results_to_csv(results)
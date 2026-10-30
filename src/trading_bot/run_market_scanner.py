import concurrent.futures
import logging
from threading import Lock
import numpy as np
import pandas as pd
import yfinance as yf

# 1. Configuration du Logger
logging.basicConfig(
    filename="market_scanner.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logging.getLogger("yfinance").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)

print_lock = Lock()


def fetch_index_tickers() -> dict:
    """Récupère automatiquement la liste complète des composants des principaux indices mondiaux."""
    markets = {}
    print("--> Récupération dynamique des composants des indices globaux...")

    # CAC 40
    try:
        url = "https://en.wikipedia.org/wiki/CAC_40"
        tables = pd.read_html(url)
        cac_df = tables[4] if len(tables) > 4 else tables[3]
        ticker_col = [c for c in cac_df.columns if "Ticker" in str(c)][0]
        markets["France (CAC 40)"] = list(cac_df[ticker_col].dropna().unique())
    except Exception as e:
        logging.error(f"Erreur CAC 40: {e}")
        markets["France (CAC 40)"] = [
            "MC.PA",
            "TTE.PA",
            "OR.PA",
            "SAN.PA",
            "AIR.PA",
            "BNP.PA",
            "SU.PA",
            "RMS.PA",
        ]

    # DAX 40
    try:
        url = "https://en.wikipedia.org/wiki/DAX"
        tables = pd.read_html(url)
        dax_df = tables[4] if len(tables) > 4 else tables[3]
        ticker_col = [
            c for c in dax_df.columns if "Ticker" in str(c) or "Symbol" in str(c)
        ][0]
        markets["Allemagne (DAX)"] = list(dax_df[ticker_col].dropna().unique())
    except Exception as e:
        logging.error(f"Erreur DAX: {e}")
        markets["Allemagne (DAX)"] = [
            "SAP.DE",
            "SIE.DE",
            "ALV.DE",
            "MBG.DE",
            "DTG.DE",
            "VOW3.DE",
            "BMW.DE",
        ]

    # S&P 500
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        tables = pd.read_html(url)
        sp_df = tables[0]
        ticker_col = "Symbol"
        tickers = sp_df[ticker_col].str.replace(".", "-", regex=False).tolist()
        markets["États-Unis (S&P 500)"] = tickers
    except Exception as e:
        logging.error(f"Erreur S&P 500: {e}")
        markets["États-Unis (S&P 500)"] = [
            "AAPL",
            "MSFT",
            "NVDA",
            "AMZN",
            "GOOGL",
            "META",
            "TSLA",
            "BRK-B",
            "JNJ",
            "JPM",
        ]

    # NASDAQ 100
    try:
        url = "https://en.wikipedia.org/wiki/Nasdaq-100"
        tables = pd.read_html(url)
        nasdaq_df = tables[4] if len(tables) > 4 else tables[3]
        ticker_col = [c for c in nasdaq_df.columns if "Ticker" in str(c)][0]
        markets["États-Unis (NASDAQ 100)"] = list(
            nasdaq_df[ticker_col].dropna().unique()
        )
    except Exception as e:
        logging.error(f"Erreur NASDAQ 100: {e}")

    # FTSE 100
    try:
        url = "https://en.wikipedia.org/wiki/FTSE_100_Index"
        tables = pd.read_html(url)
        ftse_df = tables[4] if len(tables) > 4 else tables[3]
        ticker_col = [c for c in ftse_df.columns if "Ticker" in str(c)][0]
        markets["Royaume-Uni (FTSE 100)"] = [
            f"{t}.L"
            for t in ftse_df[ticker_col].dropna().astype(str).str.strip()
        ]
    except Exception as e:
        logging.error(f"Erreur FTSE 100: {e}")

    # Macro, Forex & Crypto
    markets["Forex"] = [
        "EURUSD=X",
        "GBPUSD=X",
        "USDJPY=X",
        "EURGBP=X",
        "AUDUSD=X",
        "USDCAD=X",
    ]
    markets["Matières Premières"] = [
        "GC=F",
        "CL=F",
        "SI=F",
        "HG=F",
        "NG=F",
        "ZC=F",
    ]
    markets["Crypto-monnaies"] = [
        "BTC-USD",
        "ETH-USD",
        "SOL-USD",
        "BNB-USD",
        "XRP-USD",
        "ADA-USD",
    ]

    total_tickers = sum(len(t) for t in markets.values())
    print(
        f"--> Total des composants chargés : {total_tickers} actifs répartis sur {len(markets)} indices/classes."
    )
    return markets


# --- INDICATEURS TECHNIQUES ---


def calculate_rsi(series: pd.Series, period: int = 14) -> float:
    """Calcule le RSI (Relative Strength Index)."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return float(rsi.iloc[-1])


def calculate_macd(
    series: pd.Series, fast: int = 12, slow: int = 26, signal_period: int = 9
) -> tuple:
    """Calcule le MACD et la ligne de Signal."""
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    return float(macd_line.iloc[-1]), float(signal_line.iloc[-1])


def calculate_atr(df: pd.DataFrame, period: int = 14) -> float:
    """Calcule l'ATR (Average True Range) pour le calcul du Stop-Loss / Take-Profit."""
    high = df["High"].squeeze()
    low = df["Low"].squeeze()
    close = df["Close"].squeeze()

    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return float(atr.iloc[-1])


def process_ticker(ticker: str, market: str) -> dict:
    """Récupère les données multi-périodes, effectue l'analyse multi-indicateurs et émet le signal."""
    try:
        # Data Intraday (1H) pour indicateurs courts
        data_1h = yf.download(
            ticker, period="1mo", interval="1h", progress=False
        )
        # Data Journalière (1D) pour la tendance globale (SMA 200)
        data_1d = yf.download(
            ticker, period="1y", interval="1d", progress=False
        )

        if data_1h.empty or data_1d.empty or len(data_1d) < 50:
            return None

        close_1h = (
            data_1h["Close"].squeeze()
            if isinstance(data_1h["Close"], pd.DataFrame)
            else data_1h["Close"]
        )
        volume_1h = (
            data_1h["Volume"].squeeze()
            if isinstance(data_1h["Volume"], pd.DataFrame)
            else data_1h["Volume"]
        )
        close_1d = (
            data_1d["Close"].squeeze()
            if isinstance(data_1d["Close"], pd.DataFrame)
            else data_1d["Close"]
        )

        current_price = float(close_1h.iloc[-1])
        avg_volume = (
            float(volume_1h.mean()) if not volume_1h.empty else 100000.0
        )
        is_macro_or_crypto = any(
            kw in market for kw in ["Forex", "Matières", "Crypto"]
        )

        if not is_macro_or_crypto and avg_volume < 100000:
            return None

        # 1. Tendance de Fond (SMA 200 Daily)
        sma_200 = float(
            close_1d.rolling(window=min(200, len(close_1d))).mean().iloc[-1]
        )
        trend = "BULLISH" if current_price >= sma_200 else "BEARISH"

        # 2. RSI (14h)
        rsi = calculate_rsi(close_1h, period=14)

        # 3. MACD (12, 26, 9)
        macd, macd_signal = calculate_macd(close_1h)
        macd_momentum = "BULLISH" if macd > macd_signal else "BEARISH"

        # 4. Volume Ratio (Actuel vs Moyenne 20h)
        last_vol = float(volume_1h.iloc[-1])
        avg_vol_20 = float(volume_1h.tail(20).mean())
        vol_ratio = (last_vol / avg_vol_20) if avg_vol_20 > 0 else 1.0

        # 5. ATR (14h) & Calcul SL / TP
        atr = calculate_atr(data_1h, period=14)

        # 6. Logique de Signal Multi-Indicateurs
        signal = "NEUTRAL"
        stop_loss = np.nan
        take_profit = np.nan

        # Cond. Achat Fort : RSI survendu + Tendance haussière + MACD positif
        if rsi < 35 and trend == "BULLISH" and macd_momentum == "BULLISH":
            signal = "STRONG BUY"
            stop_loss = round(current_price - (1.5 * atr), 2)
            take_profit = round(current_price + (3.0 * atr), 2)
        elif rsi < 35:
            signal = "BUY"
            stop_loss = round(current_price - (1.5 * atr), 2)
            take_profit = round(current_price + (3.0 * atr), 2)

        # Cond. Vente Forte : RSI suracheté + Tendance baissière + MACD négatif
        elif rsi > 65 and trend == "BEARISH" and macd_momentum == "BEARISH":
            signal = "STRONG SELL"
            stop_loss = round(current_price + (1.5 * atr), 2)
            take_profit = round(current_price - (3.0 * atr), 2)
        elif rsi > 65:
            signal = "SELL"
            stop_loss = round(current_price + (1.5 * atr), 2)
            take_profit = round(current_price - (3.0 * atr), 2)

        start_price = float(close_1h.iloc[0])
        monthly_perf = ((current_price - start_price) / start_price) * 100

        return {
            "Market": market,
            "Ticker": ticker,
            "Price": round(current_price, 2),
            "Trend_SMA200": trend,
            "RSI": round(rsi, 2),
            "MACD_State": macd_momentum,
            "Vol_Ratio": round(vol_ratio, 2),
            "ATR": round(atr, 2),
            "Perf_1M_num": round(monthly_perf, 2),
            "Perf_1M": monthly_perf,
            "Signal": signal,
            "Stop_Loss": stop_loss,
            "Take_Profit": take_profit,
        }
    except Exception as e:
        logging.error(f"Erreur lors du traitement de {ticker}: {str(e)}")
        return None


def format_val_fr(val, is_perf=False, is_price=False):
    """Formate les nombres selon la typographie française."""
    if pd.isna(val) or val is None or val == "N/A":
        return "N/A"
    try:
        if is_perf:
            return f"{val:+.2f} %".replace(".", ",")
        elif is_price:
            return f"{val:,.2f}".replace(",", " ").replace(".", ",")
        else:
            return f"{val:.2f}".replace(".", ",")
    except (ValueError, TypeError):
        return str(val)


def generate_markdown_report(df: pd.DataFrame, markets_dict: dict) -> str:
    """Génère les tableaux Markdown structurés."""
    md = []
    md.append(
        "### **Scanner de Marché Multi-Indicateurs par Région / Classe d'Actifs**\n"
    )

    headers = [
        "Marché / Indice",
        "Ticker",
        "Prix",
        "Tendance (SMA200)",
        "RSI (14)",
        "MACD",
        "Perf. 1M (%)",
        "Signal",
    ]

    for market_name in markets_dict.keys():
        market_df = df[df["Market"] == market_name]
        if not market_df.empty:
            md.append(f"#### **{market_name}**\n")
            md.append(f"| {' | '.join(headers)} |")
            md.append(f"| {':--- | ' * (len(headers) - 1)}:--- |")

            for _, row in market_df.iterrows():
                price_str = format_val_fr(row["Price"], is_price=True)
                rsi_str = format_val_fr(row["RSI"])
                perf_str = format_val_fr(row["Perf_1M"], is_perf=True)
                signal_str = f"**{row['Signal']}**"

                md.append(
                    f"| {row['Market']} | {row['Ticker']} | {price_str} | {row['Trend_SMA200']} | {rsi_str} | {row['MACD_State']} | {perf_str} | {signal_str} |"
                )

            md.append("\n---\n")

    return "\n".join(md)


def main():
    markets = fetch_index_tickers()
    results = []
    tasks = []

    print("\n=== DÉMARRAGE DU SCANNER MULTI-INDICATEURS ===")

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        for market, tickers in markets.items():
            for ticker in tickers:
                tasks.append(
                    executor.submit(process_ticker, str(ticker), market)
                )

        total_tasks = len(tasks)
        completed = 0
        for future in concurrent.futures.as_completed(tasks):
            completed += 1
            if completed % 100 == 0 or completed == total_tasks:
                print(
                    f"Progression : {completed}/{total_tasks} actifs scannés..."
                )

            res = future.result()
            if res:
                results.append(res)

    df = pd.DataFrame(results)

    if df.empty:
        print("\nAucun résultat valide récupéré.")
        return

    # Export CSV des opportunités qualifiées (Signal fort ou standard)
    export_df = df[df["Signal"].isin(["STRONG BUY", "BUY", "STRONG SELL", "SELL"])]
    export_filename = "scanner_results.csv"
    export_df.to_csv(export_filename, index=False, encoding="utf-8")

    markdown_report = generate_markdown_report(df, markets)

    with open("scanner_results.md", "w", encoding="utf-8") as f:
        f.write(markdown_report)

    # -------------------------------------------------------------
    # AFFICHAGE DES RÉSULTATS AVEC CONSIGNES ATR (SL / TP)
    # -------------------------------------------------------------
    with print_lock:
        print("\n====================================================")
        print("          RAPPORTS DES OPPRTUNITES DÉTECTÉES        ")
        print("====================================================\n")

        if not export_df.empty:
            display_df = export_df.copy()
            display_df["Prix"] = display_df["Price"].apply(
                lambda x: format_val_fr(x, is_price=True)
            )
            display_df["Stop Loss"] = display_df["Stop_Loss"].apply(
                lambda x: format_val_fr(x, is_price=True)
            )
            display_df["Take Profit"] = display_df["Take_Profit"].apply(
                lambda x: format_val_fr(x, is_price=True)
            )
            display_df["RSI"] = display_df["RSI"].apply(
                lambda x: format_val_fr(x)
            )

            cols_to_show = [
                "Market",
                "Ticker",
                "Prix",
                "Trend_SMA200",
                "RSI",
                "MACD_State",
                "Vol_Ratio",
                "Signal",
                "Stop Loss",
                "Take Profit",
            ]
            print(display_df[cols_to_show].to_string(index=False))
        else:
            print(
                "Aucun signal qualifié n'a été détecté lors de ce scan multi-indicateurs."
            )

        print("\n====================================================")
        print(
            f" Export CSV généré : {export_filename} ({len(export_df)} opportunités sur {len(df)} actifs)"
        )
        print(" Export Markdown généré : scanner_results.md")


if __name__ == "__main__":
    main()
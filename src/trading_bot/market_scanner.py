import logging
from io import StringIO
import re
from typing import List
import pandas as pd
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

class UniverseScanner:
    """Récupère dynamiquement les composants et listes fixes des marchés financiers mondiaux."""

    @staticmethod
    def _clean_ticker(ticker: str) -> str:
        ticker = str(ticker).strip()
        ticker = re.sub(r'\[.*?\]', '', ticker)
        return ticker

    @staticmethod
    def _fetch_tables(url: str) -> list:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        return pd.read_html(StringIO(response.text))

    # ==========================================
    # 1. AMÉRIQUES (NORD & SUD)
    # ==========================================
    @classmethod
    def get_us_tickers(cls) -> List[str]:
        """États-Unis (NYSE / NASDAQ) - Aucun suffixe."""
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        try:
            tables = cls._fetch_tables(url)
            df = tables[0]
            tickers = df['Symbol'].astype(str).apply(cls._clean_ticker)
            return tickers.str.replace('.', '-', regex=False).tolist()
        except Exception:
            return ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "GOOGL", "META"]

    @classmethod
    def get_canada_tickers(cls) -> List[str]:
        """Canada (Bourse de Toronto) - Suffixe .TO / .V."""
        return ["SHOP.TO", "RY.TO", "TD.TO", "CNR.TO", "ENB.TO"]

    @classmethod
    def get_mexico_tickers(cls) -> List[str]:
        """Mexique (Bolsa Mexicana de Valores) - Suffixe .MX."""
        return ["^MXX", "AMXL.MX", "WALMEX.MX", "FEMSAUBD.MX"]

    @classmethod
    def get_brazil_tickers(cls) -> List[str]:
        """Brésil (B3 Sao Paulo) - Suffixe .SA."""
        return ["^BVSP", "VALE3.SA", "PETR4.SA", "ITUB4.SA"]

    @classmethod
    def get_argentina_tickers(cls) -> List[str]:
        """Argentine (Bolsa de Buenos Aires) - Suffixe .BA."""
        return ["^MERV", "GGAL.BA", "YPFD.BA", "PAMP.BA"]

    # ==========================================
    # 2. EUROPE (OUEST, NORD, SUD, EST)
    # ==========================================
    @classmethod
    def get_france_tickers(cls) -> List[str]:
        """France (Euronext Paris) - Suffixe .PA."""
        return ["^FCHI", "MC.PA", "TTE.PA", "SAN.PA", "AIR.PA", "OR.PA", "SU.PA"]

    @classmethod
    def get_germany_tickers(cls) -> List[str]:
        """Allemagne (XETRA Frankfurt) - Suffixe .DE."""
        return ["^GDAXI", "SAP.DE", "SIE.DE", "ALV.DE", "DTG.DE", "MBG.DE"]

    @classmethod
    def get_uk_tickers(cls) -> List[str]:
        """Royaume-Uni (London Stock Exchange) - Suffixe .L."""
        return ["^FTSE", "SHEL.L", "AZN.L", "HSBA.L", "ULVR.L", "BP.L"]

    @classmethod
    def get_netherlands_tickers(cls) -> List[str]:
        """Pays-Bas (Euronext Amsterdam) - Suffixe .AS."""
        return ["^AEX", "ASML.AS", "INGA.AS", "PRX.AS", "AD.AS"]

    @classmethod
    def get_switzerland_tickers(cls) -> List[str]:
        """Suisse (SIX Swiss Exchange) - Suffixe .SW."""
        return ["^SSMI", "NESN.SW", "NOVN.SW", "ROG.SW", "UBSG.SW"]

    @classmethod
    def get_italy_tickers(cls) -> List[str]:
        """Italie (Borsa Italiana) - Suffixe .MI."""
        return ["FTSEMIB.MI", "ENEL.MI", "ISP.MI", "RACE.MI", "ENI.MI"]

    @classmethod
    def get_spain_tickers(cls) -> List[str]:
        """Espagne (Bolsa de Madrid) - Suffixe .MC."""
        return ["^IBEX", "SAN.MC", "IBE.MC", "ITX.MC", "BBVA.MC"]

    @classmethod
    def get_nordic_tickers(cls) -> List[str]:
        """Pays Nordiques (Suède .ST, Norvège .OL, Danemark .CO, Finlande .HE)."""
        return ["NOVO-B.CO", "VOLV-B.ST", "EQNR.OL", "NESTE.HE"]

    @classmethod
    def get_poland_tickers(cls) -> List[str]:
        """Pologne (Warsaw Stock Exchange) - Suffixe .WA."""
        return ["WIG20.WA", "PKO.WA", "KGH.WA", "PKN.WA"]

    # ==========================================
    # 3. ASIE - PACIFIQUE
    # ==========================================
    @classmethod
    def get_japan_tickers(cls) -> List[str]:
        """Japon (Tokyo Stock Exchange) - Suffixe .T."""
        return ["^N225", "7203.T", "6758.T", "9984.T", "6861.T"]

    @classmethod
    def get_china_hk_tickers(cls) -> List[str]:
        """Chine & Hong Kong - Suffixe .HK (HK) / .SS (Shanghai) / .SZ (Shenzhen)."""
        return ["^HSI", "0700.HK", "9988.HK", "3690.HK", "601318.SS"]

    @classmethod
    def get_india_tickers(cls) -> List[str]:
        """Inde (NSE India) - Suffixe .NS."""
        return ["^NSEI", "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS"]

    @classmethod
    def get_south_korea_tickers(cls) -> List[str]:
        """Corée du Sud (KRX) - Suffixe .KS."""
        return ["^KS11", "005930.KS", "000660.KS", "005380.KS"]

    @classmethod
    def get_taiwan_tickers(cls) -> List[str]:
        """Taïwan (TWSE) - Suffixe .TW."""
        return ["^TWII", "2330.TW", "2454.TW", "2317.TW"]

    @classmethod
    def get_singapore_tickers(cls) -> List[str]:
        """Singapour (SGX) - Suffixe .SI."""
        return ["^STI", "D05.SI", "O39.SI", "U11.SI"]

    @classmethod
    def get_australia_tickers(cls) -> List[str]:
        """Australie (ASX) - Suffixe .AX."""
        return ["^AXJO", "BHP.AX", "CBA.AX", "CSL.AX", "WDS.AX"]

    # ==========================================
    # 4. MOYEN-ORIENT & AFRIQUE
    # ==========================================
    @classmethod
    def get_saudi_arabia_tickers(cls) -> List[str]:
        """Arabie Saoudite (Tadawul) - Suffixe .SR."""
        return ["2222.SR", "1120.SR", "2010.SR"]

    @classmethod
    def get_israel_tickers(cls) -> List[str]:
        """Israël (Tel Aviv Stock Exchange) - Suffixe .TA."""
        return ["^TA125.TA", "TEVA.TA", "LUMI.TA"]

    @classmethod
    def get_south_africa_tickers(cls) -> List[str]:
        """Afrique du Sud (JSE) - Suffixe .JO."""
        return ["^J203.JO", "NPN.JO", "FSR.JO", "SOL.JO"]

    # ==========================================
    # 5. MARCHÉS GLOBAUX & TRANSVERSAUX
    # ==========================================
    @classmethod
    def get_forex_tickers(cls) -> List[str]:
        """Devises majeures et émergentes."""
        return ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "USDCHF=X", "AUDUSD=X", "USDCAD=X"]

    @classmethod
    def get_commodities_tickers(cls) -> List[str]:
        """Matières Premières (Futures)."""
        return ["GC=F", "SI=F", "CL=F", "BZ=F", "NG=F", "HG=F", "ZC=F"]

    @classmethod
    def get_crypto_tickers(cls) -> List[str]:
        """Crypto-monnaies majeures."""
        return ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD"]
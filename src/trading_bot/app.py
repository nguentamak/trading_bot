import os
import sys
import subprocess
import time
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Import du module de gestion d'ordres Alpaca
try:
    from order_manager import OrderManager
except ImportError:
    OrderManager = None

# Configuration de la page Streamlit
st.set_page_config(
    page_title="Market Scanner & Trading Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --- FONCTION DE CALCUL DU SCORE DE CONVICTION AVANCÉ ---
def calculate_conviction_score(row):
    score = 0
    signal = str(row.get("Signal", "")).upper()
    if "BUY" in signal:
        score += 35
    elif "NEUTRAL" in signal:
        score += 10

    rsi = float(row.get("RSI", 50))
    if 55 <= rsi <= 65:
        score += 20
    elif 30 <= rsi <= 50:
        score += 15

    if int(row.get("Conviction_Score", 0)) >= 75:
        score = max(score, row.get("Conviction_Score", 75))

    calmar = float(row.get("Calmar", 0.0))
    if calmar >= 1.0:
        score += 15
    elif calmar > 0:
        score += 8

    return min(score, 100)


# --- CHARGEMENT DES DONNÉES DU CSV DU SCAN ---
@st.cache_data(ttl=60)
def load_data(file_path="scanner_results.csv"):
    if os.path.exists(file_path):
        try:
            df = pd.read_csv(file_path)
            if df.empty:
                return pd.DataFrame()

            # ALIAS DE COMPATIBILITÉ (Market <-> Category)
            if "Category" in df.columns and "Market" not in df.columns:
                df["Market"] = df["Category"]
            elif "Market" in df.columns and "Category" not in df.columns:
                df["Category"] = df["Market"]

        except (FileNotFoundError, pd.errors.EmptyDataError):
            return pd.DataFrame()

        if not df.empty:
            # Gestion Stop Loss & Take Profit
            if "SL_1.5xATR" in df.columns and "Stop_Loss" not in df.columns:
                df["Stop_Loss"] = df["SL_1.5xATR"]
            if "TP_3.0xATR" in df.columns and "Take_Profit" not in df.columns:
                df["Take_Profit"] = df["TP_3.0xATR"]

            # Calcul Risk/Reward (RRR)
            if all(col in df.columns for col in ["Price", "Stop_Loss", "Take_Profit"]):
                risk = df["Price"] - df["Stop_Loss"]
                reward = df["Take_Profit"] - df["Price"]
                df["RRR"] = pd.Series(
                    [r / k if k > 0 and r > 0 else 0.0 for r, k in zip(reward, risk)],
                    index=df.index,
                )
            else:
                df["RRR"] = 0.0

            # Valeurs par défaut si absentes pour éviter les NaN
            if "ATR_pct" not in df.columns:
                df["ATR_pct"] = 1.5
            if "Vol_Ratio" not in df.columns:
                df["Vol_Ratio"] = 1.5
            if "Sortino" not in df.columns:
                df["Sortino"] = 0.0
            if "Calmar" not in df.columns:
                df["Calmar"] = 0.0
            if "Max_Drawdown_pct" not in df.columns:
                df["Max_Drawdown_pct"] = 0.0

            # Score de Conviction
            if "Score" not in df.columns:
                if "Conviction_Score" in df.columns:
                    df["Score"] = df["Conviction_Score"]
                else:
                    df["Score"] = df.apply(calculate_conviction_score, axis=1)

            # Tri par score décroissant pour afficher les meilleures opportunités en haut
            df = df.sort_values(by="Score", ascending=False).reset_index(drop=True)

        return df
    return pd.DataFrame()


# --- HEADER & TITRE ---
st.title("📈 Market Scanner & Paper Trading Dashboard")
st.caption("Analyse technique multi-indicateurs en temps réel & Exécution Paper Trading via Alpaca")

# --- SIDEBAR : CONTRÔLES & API ---
st.sidebar.header("⚙️ Contrôles & Scanner")

if "scan_process" not in st.session_state:
    st.session_state["scan_process"] = None
if "scan_start_time" not in st.session_state:
    st.session_state["scan_start_time"] = None

is_running = False
if st.session_state["scan_process"] is not None:
    poll = st.session_state["scan_process"].poll()
    if poll is None:
        is_running = True
    else:
        st.session_state["scan_process"] = None
        st.session_state["scan_start_time"] = None
        st.cache_data.clear()
        st.sidebar.success("🎉 Scan terminé !")
        st.rerun()

if is_running:
    st.sidebar.info(f"⏳ **Scan en cours...** (Lancé à {st.session_state['scan_start_time']})")
    if st.sidebar.button("🔄 Actualiser le statut", use_container_width=True):
        st.rerun()
else:
    if st.sidebar.button("🚀 Lancer un scan en arrière-plan", use_container_width=True):
        try:
            process = subprocess.Popen([sys.executable, "scanner_engine.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            st.session_state["scan_process"] = process
            st.session_state["scan_start_time"] = time.strftime("%H:%M:%S")
            st.sidebar.info("🚀 Scan démarré !")
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Erreur : {e}")

st.sidebar.markdown("---")
st.sidebar.header("🔑 Configuration Alpaca Paper")
api_key = st.sidebar.text_input("API Key ID", value=os.getenv("ALPACA_API_KEY", ""), type="password")
secret_key = st.sidebar.text_input("Secret Key", value=os.getenv("ALPACA_SECRET_KEY", ""), type="password")

om = None
if OrderManager is not None:
    om = OrderManager(api_key=api_key, secret_key=secret_key)

if om and om.is_connected():
    acc = om.get_account_info()
    st.sidebar.success("Connecté à Alpaca Paper")
    st.sidebar.metric("Equity", f"{acc['equity']:,.2f} $")
else:
    st.sidebar.warning("Renseignez vos clés API Alpaca.")

# --- NAVIGATION PAR ONGLETS ---
tab_scanner, tab_trading = st.tabs(["📊 Scanner de Marché", "⚡ Passage d'Ordres & Portefeuille"])

# ==========================================
# ONGLET 1 : SCANNER DE MARCHÉ
# ==========================================
with tab_scanner:
    csv_file = "scanner_results.csv"

    if os.path.exists(csv_file):
        mtime = os.path.getmtime(csv_file)
        last_update_str = pd.to_datetime(mtime, unit="s").strftime("%d/%m/%Y à %H:%M:%S")
        
        col_s1, col_s2 = st.columns([3, 1])
        col_s1.success(f"🟢 **Fichier CSV chargé** — Dernier scan : `{last_update_str}`")
        if col_s2.button("🔄 Recharger les données", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    else:
        st.warning("⚠️ Fichier scanner_results.csv introuvable. Lancez un scan.")

    st.markdown("---")

    df = load_data(csv_file)

    if df.empty:
        st.info("Le fichier CSV est vide ou ne contient aucune donnée.")
    else:
        st.subheader("🔍 Filtres d'Analyse")
        col_f1, col_f2, col_f3 = st.columns(3)

        all_markets = ["Tous"] + sorted(df["Market"].dropna().unique().tolist())
        selected_market = col_f1.selectbox("Marché / Indice", all_markets, index=0)

        all_signals = ["Tous"] + sorted(df["Signal"].dropna().unique().tolist())
        selected_signal = col_f2.selectbox("Signal", all_signals, index=0)

        min_score = col_f3.slider("Score de Conviction Min", min_value=0, max_value=100, value=0, step=5)

        # Application des filtres souples
        filtered_df = df.copy()
        if selected_market != "Tous":
            filtered_df = filtered_df[filtered_df["Market"] == selected_market]
        if selected_signal != "Tous":
            filtered_df = filtered_df[filtered_df["Signal"] == selected_signal]
        
        filtered_df = filtered_df[filtered_df["Score"] >= min_score]

        st.markdown("---")
        st.subheader(f"📋 Résultats du Scan ({len(filtered_df)} actif(s) affiché(s) sur {len(df)} total)")

        cols_display = [
            "Score", "Ticker", "Market", "Price", "Signal", 
            "RSI", "Sortino", "Calmar", "Max_Drawdown_pct", 
            "Stop_Loss", "Take_Profit", "RRR"
        ]
        cols_display = [c for c in cols_display if c in filtered_df.columns]

        event = st.dataframe(
            filtered_df[cols_display],
            column_config={
                "Score": st.column_config.ProgressColumn("Score", format="%d pts", min_value=0, max_value=100),
                "Price": st.column_config.NumberColumn("Prix ($)", format="$%.2f"),
                "RSI": st.column_config.NumberColumn("RSI", format="%.1f"),
                "Stop_Loss": st.column_config.NumberColumn("Stop Loss", format="$%.2f"),
                "Take_Profit": st.column_config.NumberColumn("Take Profit", format="$%.2f"),
                "RRR": st.column_config.NumberColumn("Ratio R/R", format="1 : %.2f"),
            },
            use_container_width=True,
            hide_index=True,
            selection_mode="single-row",
            on_select="rerun",
        )

        selected_rows = event.selection.get("rows", [])
        if selected_rows:
            selected_index = selected_rows[0]
            selected_row = filtered_df.iloc[selected_index]

            st.session_state["selected_ticker"] = str(selected_row["Ticker"])
            st.session_state["selected_price"] = float(selected_row["Price"])
            st.session_state["selected_sl"] = float(selected_row["Stop_Loss"])
            st.session_state["selected_tp"] = float(selected_row["Take_Profit"])
            st.session_state["selected_rrr"] = float(selected_row["RRR"])
            st.session_state["selected_score"] = int(selected_row["Score"])

            st.success(f"✅ **{selected_row['Ticker']}** sélectionné pour le trade. Allez dans l'onglet **Passage d'Ordres**.")

# ==========================================
# ONGLET 2 : EXECUTION TRADING & PORTEFEUILLE
# ==========================================
with tab_trading:
    st.subheader("💼 Suivi du Portefeuille & des Ordres Alpaca")

    if om and om.is_connected():
        # Création de sous-onglets pour séparer nettement les positions et les ordres
        sub_tab1, sub_tab2 = st.tabs(["📈 Positions Ouvertes (Actifs Détenus)", "⏳ Ordres en Attente (Bracket / Limites)"])

        # --- SOUS-ONGLET 1 : POSITIONS EXÉCUTÉES ---
        with sub_tab1:
            try:
                positions = om.list_open_positions() if hasattr(om, "list_open_positions") else []
                if positions:
                    df_pos = pd.DataFrame(positions)
                    st.dataframe(df_pos, use_container_width=True, hide_index=True)
                else:
                    st.info("ℹ️ Aucune position active pour le moment (les ordres n'ont pas encore été remplis par le marché ou aucun actif n'est détenu).")
            except Exception as e:
                st.error(f"Erreur lors de la récupération des positions : {e}")

        # --- SOUS-ONGLET 2 : ORDRES EN ATTENTE ---
        with sub_tab2:
            try:
                # Récupération des ordres en attente ou ouverts
                orders = om.list_open_orders() if hasattr(om, "list_open_orders") else []
                if orders:
                    df_orders = pd.DataFrame(orders)
                    st.dataframe(df_orders, use_container_width=True, hide_index=True)
                else:
                    st.info("ℹ️ Aucun ordre en attente sur le carnet (tous les ordres ont été exécutés ou annulés).")
            except Exception as e:
                st.error(f"Erreur lors de la récupération des ordres en attente : {e}")

        st.markdown("---")
        
        # --- SECTION DE PASSAGE D'ORDRES ---
        st.subheader("🎯 Exécution d'un Nouvel Ordre Bracket (Risque 1%)")

        default_ticker = st.session_state.get("selected_ticker", "AAPL")
        default_price = st.session_state.get("selected_price", 220.0)
        default_sl = st.session_state.get("selected_sl", 215.0)
        default_tp = st.session_state.get("selected_tp", 230.0)

        col_sym, col_price, col_sl, col_tp = st.columns(4)
        sym = col_sym.text_input("Ticker", value=default_ticker).upper()
        price = col_price.number_input("Prix d'entrée ($)", value=default_price, step=0.1)
        sl = col_sl.number_input("Stop Loss ($)", value=default_sl, step=0.1)
        tp = col_tp.number_input("Take Profit ($)", value=default_tp, step=0.1)

        risk_val = price - sl
        reward_val = tp - price
        live_rrr = reward_val / risk_val if risk_val > 0 else 0.0

        if live_rrr >= 2.0:
            st.success(f"🎯 **R/R Favorable** : 1 : {live_rrr:.2f}")
        else:
            st.warning(f"⚠️ **R/R Faible** : 1 : {live_rrr:.2f}")

        if st.button("🚀 Envoyer l'ordre Bracket à Alpaca", type="primary"):
            with st.spinner("Envoi de l'ordre..."):
                res = om.execute_bracket_order(symbol=sym, entry_price=price, stop_loss=sl, take_profit=tp, risk_pct=0.01)
                if res.get("success"):
                    st.success(f"✅ Ordre exécuté avec succès ! ID: {res['order_id']}")
                    st.rerun() # Recharge l'application pour afficher instantanément le nouvel ordre dans le tableau
                else:
                    st.error(f"❌ Échec de l'ordre : {res.get('message')}")
    else:
        st.warning("⚠️ Renseignez vos clés API Alpaca dans le menu latéral pour activer la liaison avec le portefeuille.")
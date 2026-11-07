import logging
import os
from typing import Optional, Dict, List, Any
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass
from alpaca.trading.requests import (
    MarketOrderRequest,
    TakeProfitRequest,
    StopLossRequest,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)


class OrderManager:
    """Gestionnaire d'ordres automatisé Alpaca (Paper Trading) avec gestion du risque."""

    def __init__(
        self, api_key: Optional[str] = None, secret_key: Optional[str] = None
    ):
        # Récupération des clés (Arguments > Variables d'environnement)
        self.api_key = api_key or os.getenv("ALPACA_API_KEY", "")
        self.secret_key = secret_key or os.getenv("ALPACA_SECRET_KEY", "")

        if not self.api_key or not self.secret_key:
            logging.warning("⚠️ Clés API Alpaca manquantes.")
            self.client = None
        else:
            self.client = TradingClient(
                self.api_key, self.secret_key, paper=True
            )
            logging.info(
                "--> Client Alpaca initialisé en mode Paper Trading."
            )

    def is_connected(self) -> bool:
        """Vérifie si le client est correctement configuré."""
        return self.client is not None

    def get_account_info(self) -> Dict[str, float]:
        """Récupère les métriques financières du compte."""
        if not self.is_connected():
            return {"equity": 0.0, "buying_power": 0.0, "cash": 0.0}

        try:
            account = self.client.get_account()
            return {
                "equity": float(account.equity),
                "buying_power": float(account.buying_power),
                "cash": float(account.cash),
            }
        except Exception as e:
            logging.error(f"Erreur lors de la récupération du compte : {e}")
            return {"equity": 0.0, "buying_power": 0.0, "cash": 0.0}

    def calculate_position_size(
        self, entry_price: float, stop_loss_price: float, risk_pct: float = 0.01
    ) -> int:
        """Calcule le nombre d'actions à acheter (Risque maximal de 1% du capital)."""
        account_info = self.get_account_info()
        equity = account_info.get("equity", 0.0)

        if equity <= 0:
            return 0

        max_risk_amount = equity * risk_pct  # 1% de l'Equity
        risk_per_share = abs(entry_price - stop_loss_price)

        if risk_per_share <= 0:
            return 0

        qty = int(max_risk_amount / risk_per_share)
        total_cost = qty * entry_price
        buying_power = account_info.get("buying_power", equity)

        # Ajustement au pouvoir d'achat
        if total_cost > buying_power:
            qty = int(buying_power / entry_price)

        return qty

    def execute_bracket_order(
        self,
        symbol: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        risk_pct: float = 0.01,
    ) -> Dict[str, Any]:
        """Envoie un ordre d'achat au marché de type BRACKET avec Stop-Loss et Take-Profit rattachés."""
        if not self.is_connected():
            return {
                "success": False,
                "message": "Clés API Alpaca non configurées.",
            }

        symbol_formatted = symbol.replace(".", "-")
        qty = self.calculate_position_size(entry_price, stop_loss, risk_pct)

        if qty <= 0:
            return {
                "success": False,
                "message": f"Quantité calculée égale à 0 sur {symbol} (Ratios ou capital insuffisant).",
            }

        try:
            req = MarketOrderRequest(
                symbol=symbol_formatted,
                qty=qty,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.GTC,
                order_class=OrderClass.BRACKET,  # <-- INDISPENSABLE POUR LIER LE BRACKET
                take_profit=TakeProfitRequest(
                    limit_price=round(take_profit, 2)
                ),
                stop_loss=StopLossRequest(stop_price=round(stop_loss, 2)),
            )

            order = self.client.submit_order(order_data=req)
            logging.info(f"✅ Ordre Bracket envoyé avec succès sur {symbol_formatted}")

            return {
                "success": True,
                "order_id": str(order.id),
                "qty": qty,
                "symbol": symbol_formatted,
                "status": str(order.status),
            }

        except Exception as e:
            logging.error(f"❌ Erreur lors de l'exécution sur {symbol} : {e}")
            return {"success": False, "message": str(e)}

    def list_open_positions(self) -> List[Dict[str, Any]]:
        """Récupère la liste des positions ouvertes."""
        if not self.is_connected():
            return []

        try:
            positions = self.client.get_all_positions()
            return [
                {
                    "symbol": p.symbol,
                    "qty": float(p.qty),
                    "entry_price": float(p.avg_entry_price),
                    "current_price": float(p.current_price),
                    "unrealized_pl": float(p.unrealized_pl),
                    "change_today": float(p.change_today),
                }
                for p in positions
            ]
        except Exception as e:
            logging.error(
                f"Erreur lors de la récupération des positions : {e}"
            )
            return []
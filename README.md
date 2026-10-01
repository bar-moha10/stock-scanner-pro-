# stock-scanner-pro-import json
import sqlite3
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime

@dataclass
class MarketData:
    symbol: str
    current_price: float
    rsi: float
    pe_ratio: float
    news_sentiment_score: float    # מ-(-1.0) עד 1.0
    butterfly_effect_score: float  # השפעות רוחביות
    is_credible_source: bool       # האם המידע מגיע ממקורות מאומתים (מסנן רעשי רשת)

class AdvancedAutonomousTradingAgent:
    def __init__(self, name: str, db_name: str = "trading_agent_memory.db"):
        self.name = name
        self.db_name = db_name
        self._init_db()

    def _init_db(self):
        """אתחול בסיס נתונים מקומי לשמירת היסטוריית החלטות ולמידה"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                symbol TEXT,
                action TEXT,
                horizon TEXT,
                stop_loss REAL,
                target_price REAL,
                combined_score REAL
            )
        ''')
        conn.commit()
        conn.close()

    def technical_analysis(self, data: MarketData) -> str:
        """ניתוח טכני"""
        if data.rsi < 30:
            return "BUY_TECHNICAL (Oversold)"
        elif data.rsi > 70:
            return "SELL_TECHNICAL (Overbought)"
        return "HOLD_TECHNICAL (Neutral)"

    def fundamental_analysis(self, data: MarketData) -> str:
        """ניתוח פונדמנטלי"""
        if 0 < data.pe_ratio < 15:
            return "ATTRACTIVE_VALUATION"
        elif data.pe_ratio > 35:
            return "EXPENSIVE_VALUATION"
        return "FAIR_VALUATION"

    def risk_management(self, current_price: float, action: str) -> Dict[str, float]:
        """ניהול סיכונים קשוח: חישוב Stop-Loss ו-Take-Profit"""
        if "BUY" in action:
            stop_loss = round(current_price * 0.95, 2)    # 5% הגנה למטה
            take_profit = round(current_price * 1.15, 2)  # 15% יעד רווח
            risk_reward_ratio = (take_profit - current_price) / (current_price - stop_loss)
        else:
            stop_loss = 0.0
            take_profit = 0.0
            risk_reward_ratio = 0.0

        return {
            "stop_loss": stop_loss,
            "target_price": take_profit,  # תוקן מפתח מ-"take_profit" ל-"target_price" כדי שיתאים לטבלה ב-DB
            "risk_reward_ratio": round(risk_reward_ratio, 2)
        }

    def evaluate_asset(self, data: MarketData) -> Dict:
        """שילוב נתונים, סינון רעשים חברתיים, וניהול סיכונים"""
        tech_signal = self.technical_analysis(data)
        fund_signal = self.fundamental_analysis(data)
        
        # סינון רעשים ברשתות: אם המקור לא אמין, מורידים את משקל הסנטימנט
        sentiment_weight = data.news_sentiment_score if data.is_credible_source else (data.news_sentiment_score * 0.4)
        
        # שקלול כולל
        total_score = sentiment_weight + data.butterfly_effect_score
        
        horizon = "Short-term"
        action = "WAIT / MONITOR"

        # לוגיקת החלטה
        if "BUY" in tech_signal and fund_signal in ["ATTRACTIVE_VALUATION", "FAIR_VALUATION"] and total_score > 0.15:
            action = "STRONG_BUY"
            horizon = "Medium-to-Long term" if fund_signal == "ATTRACTIVE_VALUATION" else "Short-term swing"
        elif "SELL" in tech_signal or total_score < -0.4:
            action = "SELL / EXIT"
            horizon = "Immediate"

        # הפעלת מודול ניהול סיכונים
        risk_params = self.risk_management(data.current_price, action)

        decision = {
            "agent": self.name,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "symbol": data.symbol,
            "action": action,
            "suggested_horizon": horizon,
            "technical_view": tech_signal,
            "fundamental_view": fund_signal,
            "combined_score": round(total_score, 2),
            **risk_params
        }

        # שמירה בזיכרון (Feedback Loop / DB)
        self._save_decision(decision)
        return decision

    def _save_decision(self, decision: Dict):
        """שומר את ההחלטה למסד הנתונים לבדיקות עתידיות"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO decisions (timestamp, symbol, action, horizon, stop_loss, target_price, combined_score)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            decision["timestamp"],
            decision["symbol"],
            decision["action"],
            decision["suggested_horizon"],
            decision["stop_loss"],
            decision["target_price"],
            decision["combined_score"]
        ))
        conn.commit()
        conn.close()

# --- דוגמה להרצה של הסוכן המשודרג ---
if __name__ == "__main__":
    agent = AdvancedAutonomousTradingAgent(name="Alpha-Agent-v2")
    
    sample_stock = MarketData(
        symbol="TEVA",
        current_price=15.80,
        rsi=27.4,             # מכירת יתר
        pe_ratio=11.2,        # תמחור אטרקטיבי
        news_sentiment_score=0.7,   # חיובי מאוד ברשתות
        butterfly_effect_score=0.4, # השפעה רוחבית חיובית
        is_credible_source=True     # סונן ואומת כמקור אמין (מונע רעשי פייק-ניוז)
    )

    decision = agent.evaluate_asset(sample_stock)
    print("--- דוח החלטה מתקדם של הסוכן (כולל ניהול סיכונים ושמירה) ---")
    print(json.dumps(decision, indent=4, ensure_ascii=False))

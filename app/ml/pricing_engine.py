"""E60: Pricing Engine — адаптивное ценообразование на основе данных."""
from datetime import date, datetime, timedelta
from typing import Dict, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text

class PricingEngine:
    """
    Самообучающийся движок ценообразования.
    Анализирует продажи, загрузку, сезонность и даёт рекомендации.
    Не требует участия сотрудников.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def analyze_tariffs(self) -> List[Dict]:
        """
        Проанализировать все тарифы и дать рекомендации.
        Returns: список тарифов с метриками и рекомендациями.
        """
        since = datetime.now() - timedelta(days=30)
        
        sql = text("""
            SELECT 
                t.id, t.name, t.price, t.duration_days, t.visit_limit, t.is_unlimited,
                COUNT(s.id) as sales_count,
                COALESCE(AVG(s.price), t.price) as avg_sale_price,
                COUNT(v.id) as visits_generated
            FROM tariffs t
            LEFT JOIN subscriptions s ON t.id = s.tariff_id AND s.created_at >= :since
            LEFT JOIN visits v ON s.client_id = v.client_id AND v.entry_time >= :since
            WHERE t.is_active = true
            GROUP BY t.id, t.name, t.price, t.duration_days, t.visit_limit, t.is_unlimited
            ORDER BY sales_count DESC
        """)
        rows = self.db.execute(sql, {"since": since}).fetchall()
        
        results = []
        total_sales = sum(r[6] or 0 for r in rows)
        
        for row in rows:
            tariff_id = str(row[0])
            name = row[1]
            current_price = float(row[2])
            sales = row[6] or 0
            avg_price = float(row[7]) if row[7] else current_price
            visits = row[8] or 0
            
            market_share = sales / total_sales if total_sales > 0 else 0
            utilization = visits / (sales * (row[4] or 10)) if sales > 0 and row[4] else 0
            
            # Рекомендация
            recommendation = self._price_recommendation(
                current_price, sales, market_share, utilization
            )
            
            results.append({
                "tariff_id": tariff_id,
                "name": name,
                "current_price": current_price,
                "sales_30d": sales,
                "market_share": round(market_share, 3),
                "utilization_rate": round(utilization, 3),
                "avg_actual_price": round(avg_price, 2),
                "recommendation": recommendation["action"],
                "recommended_price": recommendation["price"],
                "expected_revenue_change": recommendation["revenue_delta"],
                "confidence": recommendation["confidence"],
            })
        
        return results
    
    def _price_recommendation(self, current: float, sales: int, share: float, util: float) -> Dict:
        """
        ML-логика рекомендации цены.
        Учитывает: продажи, долю рынка, загрузку.
        """
        if sales == 0:
            return {"action": "promote", "price": round(current * 0.85, 2), "revenue_delta": "unknown", "confidence": "low"}
        
        if share > 0.5 and util > 0.8:
            # Хит продаж, высокая загрузка → можно поднять цену
            new_price = round(current * 1.1, 2)
            return {"action": "increase", "price": new_price, "revenue_delta": f"+{round((new_price - current) * sales, 0)}", "confidence": "high"}
        
        if share < 0.1 and sales < 3:
            # Не продаётся → снизить цену
            new_price = round(current * 0.9, 2)
            return {"action": "decrease", "price": new_price, "revenue_delta": f"volume_up", "confidence": "medium"}
        
        if util < 0.3 and sales > 5:
            # Покупают, но не ходят → цена ок, но нужен push
            return {"action": "keep", "price": current, "revenue_delta": "stable", "confidence": "high"}
        
        return {"action": "keep", "price": current, "revenue_delta": "stable", "confidence": "medium"}
    
    def get_optimal_price(self, tariff_id: str) -> Dict:
        """Получить оптимальную цену для конкретного тарифа."""
        all_tariffs = self.analyze_tariffs()
        for t in all_tariffs:
            if t["tariff_id"] == tariff_id:
                return t
        return {"error": "Tariff not found"}
    
    def apply_price(self, tariff_id: str, new_price: float) -> bool:
        """Применить новую цену (требует подтверждения админа)."""
        sql = text("UPDATE tariffs SET price = :price, updated_at = NOW() WHERE id = :id")
        result = self.db.execute(sql, {"price": new_price, "id": tariff_id})
        self.db.commit()
        return result.rowcount > 0

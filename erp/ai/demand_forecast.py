# =========================================
# التنبؤ بالطلب على المنتجات
# انحدار خطي على المبيعات اليومية التاريخية
# =========================================
from datetime import datetime, timedelta

import numpy as np
from sklearn.linear_model import LinearRegression


def forecast_demand(sales_history: list[tuple[datetime, float]], days_ahead: int = 30) -> dict:
    """يستقبل قائمة (تاريخ الطلب، الكمية) ويعيد توقع الطلب للأيام القادمة.

    يجمع المبيعات يوميًا ثم يدرّب انحدارًا خطيًا على اتجاه الزمن."""
    if not sales_history:
        return {
            "status": "no_data",
            "message": "لا توجد بيانات مبيعات كافية للتنبؤ. سجّل طلبات بيع أولًا.",
        }

    # تجميع الكميات حسب اليوم
    daily: dict = {}
    for ordered_at, quantity in sales_history:
        day = ordered_at.date()
        daily[day] = daily.get(day, 0.0) + quantity

    days = sorted(daily.keys())
    first_day = days[0]
    X = np.array([[(d - first_day).days] for d in days], dtype=float)
    y = np.array([daily[d] for d in days], dtype=float)

    if len(days) < 3:
        # بيانات قليلة: نستخدم المتوسط البسيط
        avg = float(y.mean())
        total = avg * days_ahead
        trend = "غير محدد (بيانات قليلة)"
    else:
        model = LinearRegression()
        model.fit(X, y)
        last_offset = (days[-1] - first_day).days
        future = np.array([[last_offset + i] for i in range(1, days_ahead + 1)], dtype=float)
        predictions = np.maximum(model.predict(future), 0)
        total = float(predictions.sum())
        avg = float(predictions.mean())
        slope = float(model.coef_[0])
        if slope > 0.05:
            trend = "الطلب في ازدياد 📈"
        elif slope < -0.05:
            trend = "الطلب في انخفاض 📉"
        else:
            trend = "الطلب مستقر ➡️"

    return {
        "status": "ok",
        "days_ahead": days_ahead,
        "expected_total_demand": round(total, 1),
        "expected_daily_average": round(avg, 2),
        "trend": trend,
        "history_days": len(days),
        "forecast_until": (datetime.utcnow() + timedelta(days=days_ahead)).date().isoformat(),
    }


def reorder_suggestion(current_quantity: float, reorder_point: float, expected_daily_demand: float,
                       lead_time_days: int = 7) -> dict:
    """اقتراح ذكي لإعادة الطلب: هل تكفي الكمية الحالية حتى وصول الشحنة القادمة؟"""
    demand_during_lead = expected_daily_demand * lead_time_days
    days_of_stock = current_quantity / expected_daily_demand if expected_daily_demand > 0 else float("inf")
    should_reorder = current_quantity <= reorder_point or current_quantity < demand_during_lead
    suggested_qty = max(0.0, demand_during_lead * 2 - current_quantity) if should_reorder else 0.0

    return {
        "should_reorder": should_reorder,
        "days_of_stock_remaining": round(days_of_stock, 1) if days_of_stock != float("inf") else None,
        "suggested_order_quantity": round(suggested_qty, 1),
        "message": (
            "⚠️ يُنصح بإعادة الطلب الآن لتجنّب نفاد المخزون."
            if should_reorder
            else "✅ المخزون كافٍ حاليًا."
        ),
    }

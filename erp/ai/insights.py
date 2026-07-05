# =========================================
# الرؤى الذكية الشاملة
# يجمع كل إشارات الذكاء الاصطناعي (صيانة تنبؤية، مخزون،
# جودة، طلب) في قائمة توصيات واحدة مرتبة بالأولوية —
# تقرير الصباح الذي يقرأه مدير المصنع في دقيقة.
# =========================================
from sqlalchemy.orm import Session

from .. import models
from .anomaly_detection import detect_production_anomalies
from .demand_forecast import forecast_demand, reorder_suggestion
from .predictive_maintenance import predict_failure

# ترتيب الأولويات: 1 حرج، 2 مرتفع، 3 متوسط، 4 معلومة
PRIORITY_LABELS = {1: "🔴 حرج", 2: "🟠 مرتفع", 3: "🟡 متوسط", 4: "🔵 معلومة"}


def _machine_insights(db: Session) -> list[dict]:
    insights = []
    for machine in db.query(models.Machine).all():
        reading = (
            db.query(models.SensorReading)
            .filter_by(machine_id=machine.id)
            .order_by(models.SensorReading.recorded_at.desc())
            .first()
        )
        if not reading:
            continue
        prediction = predict_failure(
            reading.temperature, reading.vibration, reading.pressure, reading.running_hours
        )
        p = prediction["failure_probability"]
        if p >= 0.7:
            insights.append({
                "priority": 1, "category": "صيانة",
                "title": f"الآلة «{machine.name}» في خطر عطل وشيك ({p:.0%})",
                "recommendation": prediction["recommendation"],
            })
        elif p >= 0.4:
            insights.append({
                "priority": 2, "category": "صيانة",
                "title": f"الآلة «{machine.name}» بحاجة لصيانة وقائية ({p:.0%})",
                "recommendation": prediction["recommendation"],
            })
    return insights


def _inventory_insights(db: Session) -> list[dict]:
    insights = []
    for product in db.query(models.Product).all():
        if product.quantity > product.reorder_point:
            continue
        history = [
            (o.ordered_at, o.quantity)
            for o in db.query(models.SalesOrder)
            .filter_by(product_id=product.id)
            .filter(models.SalesOrder.status != "cancelled")
            .all()
        ]
        forecast = forecast_demand(history, days_ahead=30)
        daily = forecast.get("expected_daily_average", 0) or 0
        suggestion = reorder_suggestion(product.quantity, product.reorder_point, daily)
        days_left = suggestion.get("days_of_stock_remaining")
        critical = days_left is not None and days_left < 7
        insights.append({
            "priority": 1 if critical else 2,
            "category": "مخزون",
            "title": (
                f"مخزون «{product.name}» سينفد خلال ~{days_left:.0f} أيام"
                if critical else f"صنف «{product.name}» وصل حدّ إعادة الطلب"
            ),
            "recommendation": f"اطلب {suggestion['suggested_order_quantity']:.0f} {product.unit} الآن.",
        })
    return insights


def _quality_insights(db: Session) -> list[dict]:
    orders = [
        {
            "id": o.id,
            "planned_quantity": o.planned_quantity,
            "produced_quantity": o.produced_quantity,
            "defective_quantity": o.defective_quantity,
        }
        for o in db.query(models.ProductionOrder).filter_by(status="completed").all()
    ]
    result = detect_production_anomalies(orders)
    if result["status"] != "ok" or not result["anomalies"]:
        return []
    ids = "، ".join(str(a["order_id"]) for a in result["anomalies"][:5])
    return [{
        "priority": 2, "category": "جودة",
        "title": f"رُصد {result['anomalies_found']} أمر إنتاج بجودة شاذة (أوامر: {ids})",
        "recommendation": "راجع خط الإنتاج والمواد الخام لهذه الأوامر لتحديد سبب ارتفاع العيوب أو انخفاض الإنجاز.",
    }]


def _demand_insights(db: Session) -> list[dict]:
    insights = []
    for product in db.query(models.Product).all():
        history = [
            (o.ordered_at, o.quantity)
            for o in db.query(models.SalesOrder)
            .filter_by(product_id=product.id)
            .filter(models.SalesOrder.status != "cancelled")
            .all()
        ]
        forecast = forecast_demand(history, days_ahead=30)
        if forecast.get("status") != "ok":
            continue
        if "ازدياد" in forecast.get("trend", ""):
            expected = forecast["expected_total_demand"]
            if expected > product.quantity:
                insights.append({
                    "priority": 3, "category": "طلب",
                    "title": f"الطلب على «{product.name}» متزايد والمتوقع ({expected:.0f}) يفوق المخزون ({product.quantity:.0f})",
                    "recommendation": "خطط لزيادة الإنتاج أو الشراء لتغطية الطلب المتوقع خلال 30 يومًا.",
                })
    return insights


def generate_insights(db: Session) -> dict:
    """يجمع كل الرؤى ويرتبها بالأولوية."""
    insights = (
        _machine_insights(db)
        + _inventory_insights(db)
        + _quality_insights(db)
        + _demand_insights(db)
    )
    insights.sort(key=lambda i: i["priority"])
    for insight in insights:
        insight["priority_label"] = PRIORITY_LABELS[insight["priority"]]

    critical = sum(1 for i in insights if i["priority"] == 1)
    summary = (
        f"لديك {len(insights)} توصية"
        + (f" منها {critical} حرجة تتطلب تدخلًا فوريًا." if critical else "، لا شيء حرج حاليًا.")
        if insights else "✅ كل مؤشرات المصنع ضمن المدى الطبيعي — لا توصيات حاليًا."
    )

    return {"summary": summary, "insights_count": len(insights), "insights": insights}

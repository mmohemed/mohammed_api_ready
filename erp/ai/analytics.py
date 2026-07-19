# =========================================
# التحليلات الذكية المتقدمة
# - توقع نفاد المواد الخام (من استهلاك الإنتاج الفعلي + الأوامر المفتوحة)
# - المنتجات الأكثر ربحية
# - تحليل أسباب تأخر الإنتاج
# - أداء خطوط الإنتاج (الآلات) وأداء الموظفين
# =========================================
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from .. import models
from .predictive_maintenance import predict_failure


# ---------- 1) توقع نفاد المواد الخام ----------
def raw_material_runway(db: Session, window_days: int = 30) -> list[dict]:
    """يحسب معدل استهلاك كل مادة خام من الإنتاج الفعلي (BOM × الكميات المنتجة)
    خلال آخر N يوم، ويتوقع متى تنفد — قبل أن يحدث."""
    since = datetime.utcnow() - timedelta(days=window_days)
    completed = (
        db.query(models.ProductionOrder)
        .filter(models.ProductionOrder.status == "completed")
        .filter(models.ProductionOrder.completed_at >= since)
        .all()
    )
    # استهلاك كل مادة خام خلال النافذة
    consumption: dict[int, float] = {}
    for order in completed:
        for item in db.query(models.BOMItem).filter_by(product_id=order.product_id).all():
            consumption[item.component_id] = (
                consumption.get(item.component_id, 0.0)
                + item.quantity_per_unit * order.produced_quantity
            )

    # الاحتياج القادم من أوامر الإنتاج المفتوحة
    upcoming: dict[int, float] = {}
    open_orders = db.query(models.ProductionOrder).filter_by(status="in_progress").all()
    for order in open_orders:
        for item in db.query(models.BOMItem).filter_by(product_id=order.product_id).all():
            upcoming[item.component_id] = (
                upcoming.get(item.component_id, 0.0)
                + item.quantity_per_unit * order.planned_quantity
            )

    result = []
    for raw in db.query(models.Product).filter_by(product_type="raw").all():
        used = consumption.get(raw.id, 0.0)
        daily = used / window_days
        needed_soon = upcoming.get(raw.id, 0.0)
        days_left = round(raw.quantity / daily, 1) if daily > 0 else None
        will_run_out = (days_left is not None and days_left <= 14) or needed_soon > raw.quantity
        result.append({
            "product_id": raw.id,
            "name": raw.name,
            "quantity": raw.quantity,
            "unit": raw.unit,
            "daily_consumption": round(daily, 2),
            "upcoming_need": round(needed_soon, 1),
            "days_until_stockout": days_left,
            "at_risk": will_run_out,
            "message": (
                f"⚠️ ستنفد خلال ~{days_left:.0f} يومًا بمعدل الاستهلاك الحالي" if days_left is not None and days_left <= 14
                else f"⚠️ أوامر الإنتاج المفتوحة تحتاج {needed_soon:g} والمتاح {raw.quantity:g}" if needed_soon > raw.quantity
                else "✅ الكمية كافية بالمعدل الحالي"
            ),
        })
    result.sort(key=lambda r: (r["days_until_stockout"] is None, r["days_until_stockout"] or 0))
    return result


# ---------- 2) المنتجات الأكثر ربحية ----------
def product_profitability(db: Session) -> list[dict]:
    """يحلل مبيعات كل منتج: الإيراد، التكلفة، الربح، الهامش — مرتبة بالأكثر ربحًا."""
    result = []
    for product in db.query(models.Product).filter_by(product_type="finished").all():
        orders = (
            db.query(models.SalesOrder)
            .filter_by(product_id=product.id)
            .filter(models.SalesOrder.status != "cancelled")
            .all()
        )
        quantity = sum(o.quantity for o in orders)
        revenue = sum(o.quantity * o.unit_price for o in orders)
        cost = quantity * product.unit_cost
        profit = revenue - cost
        result.append({
            "product_id": product.id,
            "name": product.name,
            "units_sold": round(quantity, 1),
            "revenue": round(revenue, 2),
            "cost": round(cost, 2),
            "profit": round(profit, 2),
            "margin_percent": round(profit / revenue * 100, 1) if revenue else 0,
        })
    result.sort(key=lambda r: r["profit"], reverse=True)
    return result


# ---------- 3) تحليل أسباب تأخر الإنتاج ----------
def production_delays(db: Session, late_after_days: int = 3) -> dict:
    """يرصد الأوامر المتأخرة ويشخّص السبب المرجح لكل أمر:
    مواد خام ناقصة/مشتريات معلقة، آلة عالية الخطورة، أو حجم أمر كبير."""
    now = datetime.utcnow()
    late_orders = []
    for order in db.query(models.ProductionOrder).filter_by(status="in_progress").all():
        age_days = (now - order.created_at).total_seconds() / 86400
        if age_days < late_after_days:
            continue
        reasons = []

        # سبب 1: مواد خام ناقصة أو طلبات شراء معلقة
        for item in db.query(models.BOMItem).filter_by(product_id=order.product_id).all():
            component = db.get(models.Product, item.component_id)
            needed = item.quantity_per_unit * order.planned_quantity
            if component.quantity < needed:
                pending = (
                    db.query(models.PurchaseOrder)
                    .filter_by(product_id=component.id)
                    .filter(models.PurchaseOrder.status.in_(["requested", "ordered"]))
                    .first()
                )
                if pending and pending.status == "requested":
                    reasons.append(f"مادة «{component.name}» ناقصة وطلب الشراء ما زال بانتظار الاعتماد")
                elif pending:
                    reasons.append(f"مادة «{component.name}» ناقصة بانتظار استلام أمر الشراء #{pending.id}")
                else:
                    reasons.append(f"مادة «{component.name}» ناقصة ولا يوجد طلب شراء لها")

        # سبب 2: الآلة المعينة عالية الخطورة أو متوقفة
        if order.machine_id:
            machine = db.get(models.Machine, order.machine_id)
            if machine.status != "working":
                reasons.append(f"الآلة «{machine.name}» {'في الصيانة' if machine.status == 'maintenance' else 'متوقفة'}")
            else:
                reading = (
                    db.query(models.SensorReading)
                    .filter_by(machine_id=machine.id)
                    .order_by(models.SensorReading.recorded_at.desc())
                    .first()
                )
                if reading:
                    p = predict_failure(reading.temperature, reading.vibration,
                                        reading.pressure, reading.running_hours)
                    if p["failure_probability"] >= 0.6:
                        reasons.append(f"الآلة «{machine.name}» بخطر عطل مرتفع ({p['failure_probability']:.0%}) وقد تعمل ببطء")

        # سبب 3: حجم الأمر كبير مقارنة بالمتوسط
        completed = db.query(models.ProductionOrder).filter_by(status="completed").all()
        if completed:
            avg_planned = sum(o.planned_quantity for o in completed) / len(completed)
            if order.planned_quantity > avg_planned * 2:
                reasons.append(f"حجم الأمر ({order.planned_quantity:g}) ضعف متوسط الأوامر ({avg_planned:.0f})")

        product = db.get(models.Product, order.product_id)
        late_orders.append({
            "order_id": order.id,
            "product_name": product.name,
            "planned_quantity": order.planned_quantity,
            "age_days": round(age_days, 1),
            "source": order.source,
            "probable_causes": reasons or ["لا سبب واضح — راجع خط الإنتاج والعمالة"],
        })

    late_orders.sort(key=lambda o: o["age_days"], reverse=True)
    return {
        "late_threshold_days": late_after_days,
        "late_count": len(late_orders),
        "late_orders": late_orders,
        "message": (
            f"⚠️ {len(late_orders)} أمر إنتاج متأخر (أقدم من {late_after_days} أيام) — الأسباب المرجحة مرفقة"
            if late_orders else "✅ لا توجد أوامر إنتاج متأخرة"
        ),
    }


# ---------- 4) أداء خطوط الإنتاج (الآلات) ----------
def machine_performance(db: Session) -> list[dict]:
    """لكل آلة: الإنتاج، نسبة العيوب، متوسط مدة الإنجاز، وخطر العطل — بدرجة أداء."""
    result = []
    for machine in db.query(models.Machine).all():
        orders = (
            db.query(models.ProductionOrder)
            .filter_by(machine_id=machine.id, status="completed")
            .all()
        )
        produced = sum(o.produced_quantity for o in orders)
        defective = sum(o.defective_quantity for o in orders)
        defect_rate = defective / produced if produced else 0
        durations = [
            (o.completed_at - o.created_at).total_seconds() / 86400
            for o in orders if o.completed_at
        ]
        avg_days = round(sum(durations) / len(durations), 1) if durations else None

        risk = None
        reading = (
            db.query(models.SensorReading)
            .filter_by(machine_id=machine.id)
            .order_by(models.SensorReading.recorded_at.desc())
            .first()
        )
        if reading:
            risk = predict_failure(reading.temperature, reading.vibration,
                                   reading.pressure, reading.running_hours)["failure_probability"]

        # درجة أداء 0-100: تنخفض مع العيوب وخطر العطل
        score = 100.0
        score -= min(defect_rate * 400, 50)          # كل 1% عيوب = -4 نقاط (حتى -50)
        score -= (risk or 0) * 40                    # خطر العطل حتى -40
        result.append({
            "machine_id": machine.id,
            "name": machine.name,
            "status": machine.status,
            "orders_completed": len(orders),
            "total_produced": round(produced, 1),
            "defect_rate_percent": round(defect_rate * 100, 1),
            "avg_completion_days": avg_days,
            "failure_risk_percent": round((risk or 0) * 100) if risk is not None else None,
            "performance_score": round(max(score, 0)),
        })
    result.sort(key=lambda m: m["performance_score"], reverse=True)
    return result


# ---------- 5) أداء الموظفين (من الحضور) ----------
def employee_performance(db: Session, window_days: int = 30) -> list[dict]:
    """تحليل التزام الموظفين من سجلات الحضور خلال آخر N يوم:
    أيام الحضور، إجمالي الساعات، ومتوسط ساعات اليوم."""
    since = datetime.utcnow() - timedelta(days=window_days)
    result = []
    for employee in db.query(models.Employee).all():
        records = (
            db.query(models.AttendanceRecord)
            .filter_by(employee_id=employee.id)
            .filter(models.AttendanceRecord.check_in >= since)
            .all()
        )
        days_present = len({r.check_in.date() for r in records})
        total_hours = sum(
            (r.check_out - r.check_in).total_seconds() / 3600
            for r in records if r.check_out
        )
        result.append({
            "employee_id": employee.id,
            "name": employee.name,
            "department": employee.department,
            "days_present": days_present,
            "total_hours": round(total_hours, 1),
            "avg_hours_per_day": round(total_hours / days_present, 1) if days_present else 0,
        })
    result.sort(key=lambda e: e["total_hours"], reverse=True)
    return result

# =========================================
# المساعد الذكي للمصنع (يجيب بالعربية)
# يفهم أسئلة عن المخزون والآلات والإنتاج والمبيعات
# ويجيب من بيانات قاعدة البيانات مباشرة
# =========================================
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models


def _inventory_answer(db: Session) -> str:
    products = db.query(models.Product).all()
    if not products:
        return "لا توجد منتجات مسجلة في المخزون بعد."
    low = [p for p in products if p.quantity <= p.reorder_point]
    total_value = sum(p.quantity * p.unit_cost for p in products)
    answer = f"لديك {len(products)} صنفًا في المخزون بقيمة إجمالية تقارب {total_value:,.0f}."
    if low:
        names = "، ".join(p.name for p in low[:5])
        answer += f" ⚠️ هناك {len(low)} صنف وصل حدّ إعادة الطلب: {names}."
    else:
        answer += " ✅ لا توجد أصناف تحت حد إعادة الطلب."
    return answer


def _machines_answer(db: Session) -> str:
    machines = db.query(models.Machine).all()
    if not machines:
        return "لا توجد آلات مسجلة بعد."
    working = sum(1 for m in machines if m.status == "working")
    maintenance = sum(1 for m in machines if m.status == "maintenance")
    stopped = sum(1 for m in machines if m.status == "stopped")
    return (
        f"عدد الآلات {len(machines)}: {working} تعمل، {maintenance} في الصيانة، {stopped} متوقفة. "
        "استخدم /machines/{id}/predict-failure لتقييم خطر العطل لأي آلة."
    )


def _production_answer(db: Session) -> str:
    total = db.query(models.ProductionOrder).count()
    if total == 0:
        return "لا توجد أوامر إنتاج بعد."
    in_progress = db.query(models.ProductionOrder).filter_by(status="in_progress").count()
    completed = db.query(models.ProductionOrder).filter_by(status="completed").count()
    produced = db.query(func.coalesce(func.sum(models.ProductionOrder.produced_quantity), 0)).scalar()
    defective = db.query(func.coalesce(func.sum(models.ProductionOrder.defective_quantity), 0)).scalar()
    defect_rate = (defective / produced * 100) if produced else 0
    return (
        f"أوامر الإنتاج: {total} إجمالًا ({in_progress} قيد التنفيذ، {completed} مكتملة). "
        f"إجمالي الإنتاج {produced:,.0f} وحدة بنسبة عيوب {defect_rate:.1f}%."
    )


def _sales_answer(db: Session) -> str:
    total_orders = db.query(models.SalesOrder).count()
    if total_orders == 0:
        return "لا توجد طلبات بيع مسجلة بعد."
    revenue = db.query(
        func.coalesce(func.sum(models.SalesOrder.quantity * models.SalesOrder.unit_price), 0)
    ).filter(models.SalesOrder.status != "cancelled").scalar()
    top = (
        db.query(models.Product.name, func.sum(models.SalesOrder.quantity).label("qty"))
        .join(models.SalesOrder, models.SalesOrder.product_id == models.Product.id)
        .group_by(models.Product.id)
        .order_by(func.sum(models.SalesOrder.quantity).desc())
        .first()
    )
    answer = f"عدد طلبات البيع {total_orders} بإيرادات إجمالية {revenue:,.0f}."
    if top:
        answer += f" المنتج الأكثر مبيعًا: {top[0]} ({top[1]:,.0f} وحدة)."
    return answer


def _employees_answer(db: Session) -> str:
    total = db.query(models.Employee).count()
    if total == 0:
        return "لا يوجد موظفون مسجلون بعد."
    payroll = db.query(func.coalesce(func.sum(models.Employee.salary), 0)).scalar()
    return f"عدد الموظفين {total} وإجمالي الرواتب الشهرية {payroll:,.0f}."


# كلمات مفتاحية -> دالة الإجابة
TOPICS = [
    (("مخزون", "مخزن", "بضاعة", "أصناف", "اصناف", "منتجات", "كمية"), _inventory_answer),
    (("آلة", "الة", "آلات", "الات", "ماكينة", "مكينة", "صيانة", "عطل", "أعطال", "اعطال"), _machines_answer),
    (("إنتاج", "انتاج", "تصنيع", "جودة", "عيوب"), _production_answer),
    (("مبيعات", "بيع", "طلبات", "إيرادات", "ايرادات", "عملاء", "زبائن", "أرباح", "ارباح"), _sales_answer),
    (("موظف", "موظفين", "عمال", "عامل", "رواتب", "راتب"), _employees_answer),
]


def answer_question(question: str, db: Session) -> dict:
    """يحلل السؤال العربي بالكلمات المفتاحية ويجيب من بيانات المصنع الفعلية."""
    matched = []
    for keywords, handler in TOPICS:
        if any(kw in question for kw in keywords):
            matched.append(handler(db))

    if not matched:
        matched.append(
            "لم أفهم السؤال تمامًا. جرّب السؤال عن: المخزون، الآلات والصيانة، "
            "الإنتاج والجودة، المبيعات، أو الموظفين."
        )

    return {"question": question, "answer": " ".join(matched)}

# =========================================
# لوحة المؤشرات + المساعد الذكي
# =========================================
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

import logging

from .. import models, schemas
from ..ai import llm_assistant
from ..ai.assistant import answer_question
from ..ai.insights import generate_insights
from ..database import get_db

logger = logging.getLogger("erp.ai")

router = APIRouter(tags=["لوحة التحكم والمساعد الذكي"])


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    """ملخص مؤشرات المصنع (KPIs) في نظرة واحدة."""
    products = db.query(models.Product).all()
    low_stock = sum(1 for p in products if p.quantity <= p.reorder_point)
    inventory_value = sum(p.quantity * p.unit_cost for p in products)

    machines_total = db.query(models.Machine).count()
    machines_working = db.query(models.Machine).filter_by(status="working").count()

    produced = db.query(func.coalesce(func.sum(models.ProductionOrder.produced_quantity), 0)).scalar()
    defective = db.query(func.coalesce(func.sum(models.ProductionOrder.defective_quantity), 0)).scalar()
    in_progress = db.query(models.ProductionOrder).filter_by(status="in_progress").count()

    revenue = db.query(
        func.coalesce(func.sum(models.SalesOrder.quantity * models.SalesOrder.unit_price), 0)
    ).filter(models.SalesOrder.status != "cancelled").scalar()

    return {
        "inventory": {
            "products_count": len(products),
            "low_stock_items": low_stock,
            "inventory_value": round(inventory_value, 2),
        },
        "machines": {
            "total": machines_total,
            "working": machines_working,
            "availability_rate": round(machines_working / machines_total, 3) if machines_total else None,
        },
        "production": {
            "orders_in_progress": in_progress,
            "total_produced": produced,
            "defect_rate": round(defective / produced, 4) if produced else 0,
        },
        "sales": {
            "orders_count": db.query(models.SalesOrder).count(),
            "total_revenue": round(revenue, 2),
        },
        "employees_count": db.query(models.Employee).count(),
    }


@router.get("/dashboard/sales-timeseries")
def sales_timeseries(days: int = 30, db: Session = Depends(get_db)):
    """المبيعات اليومية (كمية وإيراد) لآخر N يوم — تغذي مخطط اللوحة."""
    from datetime import datetime, timedelta

    days = max(1, min(days, 365))
    since = datetime.utcnow() - timedelta(days=days)
    orders = (
        db.query(models.SalesOrder)
        .filter(models.SalesOrder.status != "cancelled")
        .filter(models.SalesOrder.ordered_at >= since)
        .all()
    )
    daily: dict = {}
    for o in orders:
        day = o.ordered_at.date().isoformat()
        entry = daily.setdefault(day, {"quantity": 0.0, "revenue": 0.0})
        entry["quantity"] += o.quantity
        entry["revenue"] += o.quantity * o.unit_price

    series = [
        {"date": day, "quantity": round(v["quantity"], 1), "revenue": round(v["revenue"], 2)}
        for day, v in sorted(daily.items())
    ]
    return {"days": days, "series": series}


@router.post("/ai/assistant")
def ai_assistant(body: schemas.AssistantQuestion, db: Session = Depends(get_db)):
    """🤖 اسأل المساعد الذكي بالعربية عن أي شيء في المصنع.

    عند تعريف ANTHROPIC_API_KEY يجيب نموذج Claude على أسئلة حرة ومعقدة
    اعتمادًا على بيانات المصنع الحية؛ وإلا يجيب المساعد القاعدي المدمج.
    """
    if llm_assistant.is_configured():
        try:
            return llm_assistant.ask_claude(body.question, db)
        except Exception as exc:
            logger.warning("تعذر الوصول لنموذج Claude، الرجوع للمساعد القاعدي: %s", exc)
    return {**answer_question(body.question, db), "engine": "rules"}


@router.get("/ai/insights")
def ai_insights(db: Session = Depends(get_db)):
    """🤖 تقرير الرؤى الذكية: كل توصيات الذكاء الاصطناعي (صيانة، مخزون،
    جودة، طلب) مجمّعة ومرتبة بالأولوية — تقرير الصباح لمدير المصنع."""
    return generate_insights(db)

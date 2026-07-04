# =========================================
# المساعد الذكي المتقدم (Claude)
# يجيب على أسئلة حرة ومعقدة بالعربية اعتمادًا على
# لقطة حية من بيانات المصنع تُمرَّر للنموذج مع السؤال.
#
# التفعيل: عرّف متغير البيئة ANTHROPIC_API_KEY
# بدون المفتاح يعمل النظام تلقائيًا بالمساعد القاعدي (assistant.py)
# =========================================
import json
import os

from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models
from .predictive_maintenance import predict_failure

MODEL = os.environ.get("ERP_CLAUDE_MODEL", "claude-opus-4-8")

SYSTEM_PROMPT = (
    "أنت مساعد ذكي لنظام ERP في مصنع. تجيب بالعربية الفصحى المبسطة وبإيجاز مفيد.\n"
    "ستصلك لقطة JSON من بيانات المصنع الحالية (مخزون، آلات، إنتاج، مبيعات، موظفون) ثم سؤال المستخدم.\n"
    "قواعدك:\n"
    "- أجب من البيانات المرفقة فقط، ولا تختلق أرقامًا غير موجودة فيها.\n"
    "- إن كان السؤال خارج نطاق بيانات المصنع فقل ذلك بأدب واقترح ما يمكنك الإجابة عنه.\n"
    "- عند وجود مخاطر (آلة على وشك عطل، مخزون ينفد، شذوذ جودة) نبّه إليها حتى لو لم يسأل عنها مباشرة.\n"
    "- قدّم توصية عملية واحدة على الأقل عندما يكون ذلك مناسبًا."
)


def is_configured() -> bool:
    """هل مساعد Claude مفعّل؟ (يوجد مفتاح API ومكتبة anthropic مثبتة)"""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return False
    try:
        import anthropic  # noqa: F401
        return True
    except ImportError:
        return False


def build_factory_snapshot(db: Session) -> dict:
    """لقطة مضغوطة من بيانات المصنع تكفي للإجابة على معظم الأسئلة."""
    products = db.query(models.Product).all()
    snapshot_products = [
        {
            "name": p.name, "sku": p.sku, "quantity": p.quantity,
            "reorder_point": p.reorder_point, "unit_price": p.unit_price,
            "low_stock": p.quantity <= p.reorder_point,
        }
        for p in products
    ]

    machines = []
    for m in db.query(models.Machine).all():
        entry = {"name": m.name, "type": m.machine_type, "status": m.status}
        reading = (
            db.query(models.SensorReading)
            .filter_by(machine_id=m.id)
            .order_by(models.SensorReading.recorded_at.desc())
            .first()
        )
        if reading:
            prediction = predict_failure(
                reading.temperature, reading.vibration, reading.pressure, reading.running_hours
            )
            entry["failure_probability"] = prediction["failure_probability"]
            entry["risk_level"] = prediction["risk_level"]
        machines.append(entry)

    produced = db.query(func.coalesce(func.sum(models.ProductionOrder.produced_quantity), 0)).scalar()
    defective = db.query(func.coalesce(func.sum(models.ProductionOrder.defective_quantity), 0)).scalar()
    revenue = db.query(
        func.coalesce(func.sum(models.SalesOrder.quantity * models.SalesOrder.unit_price), 0)
    ).filter(models.SalesOrder.status != "cancelled").scalar()

    return {
        "products": snapshot_products,
        "machines": machines,
        "production": {
            "orders_total": db.query(models.ProductionOrder).count(),
            "in_progress": db.query(models.ProductionOrder).filter_by(status="in_progress").count(),
            "total_produced": produced,
            "defect_rate_percent": round(defective / produced * 100, 2) if produced else 0,
        },
        "sales": {
            "orders_count": db.query(models.SalesOrder).count(),
            "total_revenue": revenue,
        },
        "employees_count": db.query(models.Employee).count(),
    }


def ask_claude(question: str, db: Session) -> dict:
    """يسأل نموذج Claude مع لقطة بيانات المصنع. يرمي استثناء عند فشل الاتصال —
    المستدعي مسؤول عن الرجوع للمساعد القاعدي."""
    import anthropic

    snapshot = json.dumps(build_factory_snapshot(db), ensure_ascii=False, sort_keys=True)
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=[{
            "role": "user",
            "content": f"بيانات المصنع الحالية (JSON):\n{snapshot}\n\nسؤال المستخدم: {question}",
        }],
    )

    if response.stop_reason == "refusal":
        return {
            "question": question,
            "answer": "تعذر على المساعد الإجابة عن هذا السؤال.",
            "engine": "claude",
        }

    answer = "".join(block.text for block in response.content if block.type == "text")
    return {"question": question, "answer": answer, "engine": "claude", "model": response.model}

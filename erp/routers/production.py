# =========================================
# أوامر الإنتاج + كشف شذوذ الجودة بالذكاء الاصطناعي
# =========================================
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..ai.anomaly_detection import detect_production_anomalies
from ..auth import require_writer
from ..database import get_db

router = APIRouter(prefix="/production", tags=["الإنتاج والجودة"])


@router.post("/orders", response_model=schemas.ProductionOrderOut)
def create_order(order: schemas.ProductionOrderCreate, db: Session = Depends(get_db),
                 _: object = Depends(require_writer)):
    if not db.get(models.Product, order.product_id):
        raise HTTPException(status_code=404, detail="المنتج غير موجود")
    if order.machine_id and not db.get(models.Machine, order.machine_id):
        raise HTTPException(status_code=404, detail="الآلة غير موجودة")
    row = models.ProductionOrder(**order.model_dump(), status="in_progress")
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/orders", response_model=list[schemas.ProductionOrderOut])
def list_orders(db: Session = Depends(get_db)):
    return db.query(models.ProductionOrder).all()


@router.post("/orders/{order_id}/complete", response_model=schemas.ProductionOrderOut)
def complete_order(order_id: int, report: schemas.ProductionReport, db: Session = Depends(get_db),
                 _: object = Depends(require_writer)):
    """إكمال أمر إنتاج: تسجيل الكمية المنتجة والمعيبة وإضافة الصافي للمخزون."""
    order = db.get(models.ProductionOrder, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="أمر الإنتاج غير موجود")
    if order.status == "completed":
        raise HTTPException(status_code=400, detail="الأمر مكتمل بالفعل")
    if report.defective_quantity > report.produced_quantity:
        raise HTTPException(status_code=400, detail="الكمية المعيبة لا يمكن أن تتجاوز المنتجة")

    order.produced_quantity = report.produced_quantity
    order.defective_quantity = report.defective_quantity
    order.status = "completed"
    order.completed_at = datetime.utcnow()

    # الوحدات السليمة تدخل المخزون
    product = db.get(models.Product, order.product_id)
    product.quantity += report.produced_quantity - report.defective_quantity

    db.commit()
    db.refresh(order)
    return order


@router.get("/quality/anomalies")
def quality_anomalies(db: Session = Depends(get_db)):
    """🤖 كشف أوامر الإنتاج ذات الجودة الشاذة (Isolation Forest)."""
    orders = [
        {
            "id": o.id,
            "planned_quantity": o.planned_quantity,
            "produced_quantity": o.produced_quantity,
            "defective_quantity": o.defective_quantity,
        }
        for o in db.query(models.ProductionOrder).filter_by(status="completed").all()
    ]
    return detect_production_anomalies(orders)

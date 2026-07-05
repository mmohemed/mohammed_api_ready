# =========================================
# إدارة المخزون + اقتراحات إعادة الطلب الذكية
# =========================================
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..ai.demand_forecast import forecast_demand, reorder_suggestion
from ..auth import require_writer
from ..database import get_db

router = APIRouter(prefix="/inventory", tags=["المخزون"])


@router.post("/products", response_model=schemas.ProductOut)
def create_product(product: schemas.ProductCreate, db: Session = Depends(get_db),
                 _: object = Depends(require_writer)):
    if db.query(models.Product).filter_by(sku=product.sku).first():
        raise HTTPException(status_code=400, detail="يوجد منتج بنفس رمز SKU")
    row = models.Product(**product.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/products", response_model=list[schemas.ProductOut])
def list_products(db: Session = Depends(get_db)):
    return db.query(models.Product).all()


@router.get("/products/{product_id}", response_model=schemas.ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.get(models.Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="المنتج غير موجود")
    return product


@router.put("/products/{product_id}", response_model=schemas.ProductOut)
def update_product(product_id: int, changes: schemas.ProductUpdate, db: Session = Depends(get_db),
                   _: object = Depends(require_writer)):
    product = db.get(models.Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="المنتج غير موجود")
    for field, value in changes.model_dump(exclude_none=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


@router.delete("/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db),
                   _: object = Depends(require_writer)):
    product = db.get(models.Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="المنتج غير موجود")
    has_moves = (
        db.query(models.SalesOrder).filter_by(product_id=product_id).first()
        or db.query(models.ProductionOrder).filter_by(product_id=product_id).first()
    )
    if has_moves:
        raise HTTPException(
            status_code=400,
            detail="لا يمكن حذف منتج له حركات مبيعات أو إنتاج — للحفاظ على سجلات النظام",
        )
    db.delete(product)
    db.commit()
    return {"message": "تم حذف المنتج بنجاح"}


@router.post("/products/{product_id}/adjust", response_model=schemas.ProductOut)
def adjust_stock(product_id: int, adjustment: schemas.StockAdjust, db: Session = Depends(get_db),
                 _: object = Depends(require_writer)):
    product = db.get(models.Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="المنتج غير موجود")
    if product.quantity + adjustment.change < 0:
        raise HTTPException(status_code=400, detail="لا يمكن سحب كمية أكبر من المتوفر")
    product.quantity += adjustment.change
    db.commit()
    db.refresh(product)
    return product


@router.get("/alerts")
def low_stock_alerts(db: Session = Depends(get_db)):
    """تنبيهات الأصناف التي وصلت حدّ إعادة الطلب مع اقتراح كمية ذكي."""
    alerts = []
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
        daily = forecast.get("expected_daily_average", 1) or 1
        suggestion = reorder_suggestion(product.quantity, product.reorder_point, daily)
        alerts.append({
            "product_id": product.id,
            "name": product.name,
            "quantity": product.quantity,
            "reorder_point": product.reorder_point,
            **suggestion,
        })
    return {"alerts_count": len(alerts), "alerts": alerts}

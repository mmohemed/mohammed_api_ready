# =========================================
# المبيعات + التنبؤ بالطلب
# =========================================
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import models, schemas
from ..ai.demand_forecast import forecast_demand
from ..database import get_db

router = APIRouter(prefix="/sales", tags=["المبيعات"])


@router.post("/orders", response_model=schemas.SalesOrderOut)
def create_sales_order(order: schemas.SalesOrderCreate, db: Session = Depends(get_db)):
    product = db.get(models.Product, order.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="المنتج غير موجود")
    if product.quantity < order.quantity:
        raise HTTPException(
            status_code=400,
            detail=f"الكمية المطلوبة غير متوفرة (المتاح: {product.quantity})",
        )

    unit_price = order.unit_price if order.unit_price is not None else product.unit_price
    row = models.SalesOrder(
        product_id=order.product_id,
        customer_name=order.customer_name,
        quantity=order.quantity,
        unit_price=unit_price,
    )
    product.quantity -= order.quantity  # خصم من المخزون
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/orders", response_model=list[schemas.SalesOrderOut])
def list_sales_orders(db: Session = Depends(get_db)):
    return db.query(models.SalesOrder).all()


@router.get("/forecast/{product_id}")
def demand_forecast(
    product_id: int,
    days_ahead: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """🤖 توقع الطلب على منتج للأيام القادمة بناءً على تاريخ المبيعات."""
    product = db.get(models.Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="المنتج غير موجود")

    history = [
        (o.ordered_at, o.quantity)
        for o in db.query(models.SalesOrder)
        .filter_by(product_id=product_id)
        .filter(models.SalesOrder.status != "cancelled")
        .all()
    ]
    forecast = forecast_demand(history, days_ahead=days_ahead)
    return {"product_id": product_id, "product_name": product.name, **forecast}

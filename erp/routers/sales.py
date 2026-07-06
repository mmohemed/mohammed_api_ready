# =========================================
# المبيعات + التنبؤ بالطلب
# =========================================
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import models, schemas, workflow
from ..ai.demand_forecast import forecast_demand
from ..auth import require_department
from ..database import get_db

router = APIRouter(prefix="/sales", tags=["المبيعات"])


@router.post("/orders", response_model=schemas.SalesOrderOut)
def create_sales_order(order: schemas.SalesOrderCreate, db: Session = Depends(get_db),
                 _: object = Depends(require_department("المبيعات"))):
    """تسجيل طلب بيع — السلسلة التلقائية:

    - الكمية متوفرة: تُخصم فورًا والحالة confirmed
    - الكمية غير كافية: الحالة pending_production ويُنشأ أمر إنتاج تلقائيًا للعجز،
      وإن نقصت المواد الخام يُنشأ طلب شراء تلقائي لقسم المشتريات
    """
    product = db.get(models.Product, order.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="المنتج غير موجود")

    unit_price = order.unit_price if order.unit_price is not None else product.unit_price
    row = models.SalesOrder(
        product_id=order.product_id,
        customer_name=order.customer_name,
        quantity=order.quantity,
        unit_price=unit_price,
    )
    db.add(row)
    db.flush()

    if product.quantity >= order.quantity:
        product.quantity -= order.quantity  # خصم فوري من المخزون
    else:
        row.status = "pending_production"
        shortage = order.quantity - product.quantity
        workflow.handle_sales_shortage(db, row, shortage)

    db.commit()
    db.refresh(row)
    return row


@router.post("/orders/{order_id}/deliver")
def deliver_order(order_id: int, db: Session = Depends(get_db),
                  _: object = Depends(require_department("المبيعات"))):
    """تسليم الطلب للعميل: تُصدر الفاتورة وتُسجل القيود المحاسبية تلقائيًا."""
    order = db.get(models.SalesOrder, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="طلب البيع غير موجود")
    if order.status not in ("confirmed", "pending_production"):
        raise HTTPException(status_code=400, detail="هذا الطلب مُسلَّم أو ملغى بالفعل")
    try:
        invoice = workflow.deliver_sales_order(db, order)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    db.commit()
    return {
        "message": "تم التسليم وإصدار الفاتورة وتسجيل القيود",
        "invoice_number": invoice.number,
        "invoice_total": invoice.total,
    }


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

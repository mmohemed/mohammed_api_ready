# =========================================
# الموردون وأوامر الشراء
# استلام أمر الشراء يضيف الكمية للمخزون ويحدّث تكلفة الوحدة
# =========================================
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, workflow
from ..auth import require_department
from ..database import get_db

router = APIRouter(prefix="/purchases", tags=["المشتريات والموردون"])


# ---------- الموردون ----------
@router.post("/suppliers", response_model=schemas.SupplierOut)
def create_supplier(supplier: schemas.SupplierCreate, db: Session = Depends(get_db),
                    _: object = Depends(require_department("المشتريات"))):
    row = models.Supplier(**supplier.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/suppliers", response_model=list[schemas.SupplierOut])
def list_suppliers(db: Session = Depends(get_db)):
    return db.query(models.Supplier).all()


@router.put("/suppliers/{supplier_id}", response_model=schemas.SupplierOut)
def update_supplier(supplier_id: int, changes: schemas.SupplierUpdate, db: Session = Depends(get_db),
                    _: object = Depends(require_department("المشتريات"))):
    supplier = db.get(models.Supplier, supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="المورد غير موجود")
    for field, value in changes.model_dump(exclude_none=True).items():
        setattr(supplier, field, value)
    db.commit()
    db.refresh(supplier)
    return supplier


@router.delete("/suppliers/{supplier_id}")
def delete_supplier(supplier_id: int, db: Session = Depends(get_db),
                    _: object = Depends(require_department("المشتريات"))):
    supplier = db.get(models.Supplier, supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="المورد غير موجود")
    if db.query(models.PurchaseOrder).filter_by(supplier_id=supplier_id).first():
        raise HTTPException(status_code=400,
                            detail="لا يمكن حذف مورد له أوامر شراء مسجلة")
    db.delete(supplier)
    db.commit()
    return {"message": "تم حذف المورد بنجاح"}


# ---------- أوامر الشراء ----------
@router.post("/orders", response_model=schemas.PurchaseOrderOut)
def create_purchase_order(order: schemas.PurchaseOrderCreate, db: Session = Depends(get_db),
                          _: object = Depends(require_department("المشتريات"))):
    if not db.get(models.Supplier, order.supplier_id):
        raise HTTPException(status_code=404, detail="المورد غير موجود")
    product = db.get(models.Product, order.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="المنتج غير موجود")
    unit_cost = order.unit_cost if order.unit_cost is not None else product.unit_cost
    row = models.PurchaseOrder(
        supplier_id=order.supplier_id, product_id=order.product_id,
        quantity=order.quantity, unit_cost=unit_cost,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/orders", response_model=list[schemas.PurchaseOrderOut])
def list_purchase_orders(db: Session = Depends(get_db)):
    return db.query(models.PurchaseOrder).all()


@router.post("/orders/{order_id}/approve", response_model=schemas.PurchaseOrderOut)
def approve_purchase_request(order_id: int, approval: schemas.PurchaseApprove,
                             db: Session = Depends(get_db),
                             _: object = Depends(require_department("المشتريات"))):
    """اعتماد طلب شراء تلقائي: تعيين المورد وتحويله إلى أمر مؤكد."""
    order = db.get(models.PurchaseOrder, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="أمر الشراء غير موجود")
    if order.status != "requested":
        raise HTTPException(status_code=400, detail="هذا الأمر ليس طلبًا بانتظار الاعتماد")
    if not db.get(models.Supplier, approval.supplier_id):
        raise HTTPException(status_code=404, detail="المورد غير موجود")
    order.supplier_id = approval.supplier_id
    if approval.unit_cost is not None:
        order.unit_cost = approval.unit_cost
    if approval.quantity is not None:
        order.quantity = approval.quantity
    order.status = "ordered"
    db.commit()
    db.refresh(order)
    return order


@router.post("/orders/{order_id}/receive", response_model=schemas.PurchaseOrderOut)
def receive_purchase_order(order_id: int, db: Session = Depends(get_db),
                           _: object = Depends(require_department("المشتريات"))):
    """استلام الشحنة: الكمية تدخل المخزون، تُحدَّث التكلفة، ويُسجَّل قيد المشتريات."""
    order = db.get(models.PurchaseOrder, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="أمر الشراء غير موجود")
    if order.status != "ordered":
        raise HTTPException(status_code=400, detail="هذا الأمر ليس بانتظار الاستلام")
    product = db.get(models.Product, order.product_id)
    product.quantity += order.quantity
    product.unit_cost = order.unit_cost
    order.status = "received"
    order.received_at = datetime.utcnow()
    workflow.record_purchase_receipt(db, order)
    db.commit()
    db.refresh(order)
    return order


@router.post("/orders/{order_id}/cancel", response_model=schemas.PurchaseOrderOut)
def cancel_purchase_order(order_id: int, db: Session = Depends(get_db),
                          _: object = Depends(require_department("المشتريات"))):
    order = db.get(models.PurchaseOrder, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="أمر الشراء غير موجود")
    if order.status not in ("ordered", "requested"):
        raise HTTPException(status_code=400, detail="لا يمكن إلغاء أمر مستلَم أو ملغى")
    order.status = "cancelled"
    db.commit()
    db.refresh(order)
    return order

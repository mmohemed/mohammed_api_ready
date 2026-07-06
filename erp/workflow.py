# =========================================
# محرك سير العمل التلقائي — قلب الـ ERP
#
# السلسلة: طلب بيع ← (عجز؟) أمر إنتاج تلقائي ← (مواد خام ناقصة؟)
#          طلب شراء تلقائي ← استلام ← إنتاج ← تسليم ← فاتورة + قيود محاسبية
# =========================================
from datetime import datetime

from sqlalchemy.orm import Session

from . import models

VAT_RATE = 0.15  # ضريبة القيمة المضافة الافتراضية


# ---------- المواد الخام (BOM) ----------
def get_bom(db: Session, product_id: int) -> list[models.BOMItem]:
    return db.query(models.BOMItem).filter_by(product_id=product_id).all()


def check_components_shortage(db: Session, product_id: int, quantity: float) -> list[dict]:
    """يفحص مكونات المنتج ويعيد قائمة النواقص [{component, needed, available, shortage}]"""
    shortages = []
    for item in get_bom(db, product_id):
        needed = item.quantity_per_unit * quantity
        component = db.get(models.Product, item.component_id)
        if component.quantity < needed:
            shortages.append({
                "component": component,
                "needed": needed,
                "available": component.quantity,
                "shortage": needed - component.quantity,
            })
    return shortages


def auto_request_components(db: Session, product_id: int, quantity: float, reference: str) -> list[models.PurchaseOrder]:
    """ينشئ طلبات شراء تلقائية (بانتظار اعتماد قسم المشتريات) للمواد الخام الناقصة."""
    requests = []
    for shortage in check_components_shortage(db, product_id, quantity):
        component = shortage["component"]
        # لا نكرر طلبًا تلقائيًا مفتوحًا لنفس المادة
        existing = (
            db.query(models.PurchaseOrder)
            .filter_by(product_id=component.id, source="auto")
            .filter(models.PurchaseOrder.status.in_(["requested", "ordered"]))
            .first()
        )
        if existing:
            continue
        po = models.PurchaseOrder(
            supplier_id=None,
            product_id=component.id,
            quantity=round(shortage["shortage"] * 1.2, 1),  # هامش أمان 20%
            unit_cost=component.unit_cost,
            status="requested",
            source="auto",
            note=f"طلب تلقائي: نقص مواد خام لـ {reference}",
        )
        db.add(po)
        requests.append(po)
    return requests


def consume_components(db: Session, product_id: int, produced_quantity: float) -> None:
    """يخصم المواد الخام من المخزون حسب مكونات المنتج عند إتمام الإنتاج."""
    for item in get_bom(db, product_id):
        component = db.get(models.Product, item.component_id)
        component.quantity = max(0.0, component.quantity - item.quantity_per_unit * produced_quantity)


# ---------- طلب البيع ← أمر إنتاج ----------
def handle_sales_shortage(db: Session, sales_order: models.SalesOrder, shortage: float) -> models.ProductionOrder:
    """ينشئ أمر إنتاج تلقائيًا لتغطية عجز طلب بيع، ويطلب المواد الخام الناقصة."""
    production = models.ProductionOrder(
        product_id=sales_order.product_id,
        sales_order_id=sales_order.id,
        planned_quantity=shortage,
        status="in_progress",
        source="auto",
    )
    db.add(production)
    db.flush()
    auto_request_components(
        db, sales_order.product_id, shortage,
        reference=f"أمر الإنتاج التلقائي #{production.id} (طلب البيع #{sales_order.id})",
    )
    return production


# ---------- القيود المحاسبية ----------
def add_journal_entry(db: Session, entry_type: str, description: str,
                      debit: str, credit: str, amount: float, reference: str = "") -> models.JournalEntry:
    entry = models.JournalEntry(
        entry_type=entry_type, description=description,
        debit_account=debit, credit_account=credit,
        amount=round(amount, 2), reference=reference,
    )
    db.add(entry)
    return entry


# ---------- التسليم ← فاتورة + قيود ----------
def deliver_sales_order(db: Session, sales_order: models.SalesOrder) -> models.Invoice:
    """يسلّم طلب البيع: يصدر فاتورة (مع الضريبة) ويسجل قيدي الإيراد وتكلفة البضاعة."""
    product = db.get(models.Product, sales_order.product_id)

    # طلب بانتظار الإنتاج: نخصم من المخزون الآن (لم يُخصم عند الإنشاء)
    if sales_order.status == "pending_production":
        if product.quantity < sales_order.quantity:
            raise ValueError(
                f"المخزون لا يكفي للتسليم بعد (المتاح: {product.quantity:g}، "
                f"المطلوب: {sales_order.quantity:g}) — أكمل أوامر الإنتاج أولًا"
            )
        product.quantity -= sales_order.quantity

    subtotal = sales_order.quantity * sales_order.unit_price
    vat = subtotal * VAT_RATE
    count = db.query(models.Invoice).count() + 1
    invoice = models.Invoice(
        number=f"INV-{count:05d}",
        sales_order_id=sales_order.id,
        subtotal=round(subtotal, 2),
        vat_rate=VAT_RATE,
        vat_amount=round(vat, 2),
        total=round(subtotal + vat, 2),
    )
    db.add(invoice)

    add_journal_entry(
        db, "sale", f"مبيعات: {product.name} × {sales_order.quantity:g} — {sales_order.customer_name}",
        debit="العملاء / النقد", credit="إيرادات المبيعات",
        amount=subtotal + vat, reference=invoice.number,
    )
    cogs = sales_order.quantity * product.unit_cost
    if cogs > 0:
        add_journal_entry(
            db, "cogs", f"تكلفة البضاعة المباعة: {product.name}",
            debit="تكلفة البضاعة المباعة", credit="المخزون",
            amount=cogs, reference=invoice.number,
        )

    sales_order.status = "delivered"
    sales_order.delivered_at = datetime.utcnow()
    return invoice


# ---------- استلام مشتريات ← قيد ----------
def record_purchase_receipt(db: Session, purchase_order: models.PurchaseOrder) -> None:
    product = db.get(models.Product, purchase_order.product_id)
    add_journal_entry(
        db, "purchase",
        f"مشتريات: {product.name} × {purchase_order.quantity:g}",
        debit="المخزون", credit="الموردون / النقد",
        amount=purchase_order.quantity * purchase_order.unit_cost,
        reference=f"PO-{purchase_order.id}",
    )

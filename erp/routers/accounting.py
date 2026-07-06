# =========================================
# المحاسبة: الفواتير والقيود والملخص المالي
# =========================================
import html

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db

router = APIRouter(prefix="/accounting", tags=["المحاسبة"])


@router.get("/invoices")
def list_invoices(db: Session = Depends(get_db)):
    result = []
    for inv in db.query(models.Invoice).order_by(models.Invoice.id.desc()).all():
        order = inv.sales_order
        product = db.get(models.Product, order.product_id) if order else None
        result.append({
            "id": inv.id, "number": inv.number,
            "customer_name": order.customer_name if order else "",
            "product_name": product.name if product else "",
            "quantity": order.quantity if order else 0,
            "subtotal": inv.subtotal, "vat_amount": inv.vat_amount, "total": inv.total,
            "issued_at": inv.issued_at,
        })
    return result


@router.get("/journal")
def list_journal_entries(db: Session = Depends(get_db)):
    return [
        {
            "id": e.id, "entry_type": e.entry_type, "description": e.description,
            "debit_account": e.debit_account, "credit_account": e.credit_account,
            "amount": e.amount, "reference": e.reference, "created_at": e.created_at,
        }
        for e in db.query(models.JournalEntry).order_by(models.JournalEntry.id.desc()).all()
    ]


@router.get("/summary")
def financial_summary(db: Session = Depends(get_db)):
    """الملخص المالي: إيرادات، تكلفة بضاعة، مشتريات، رواتب، ربح إجمالي."""
    def total(entry_type):
        return db.query(func.coalesce(func.sum(models.JournalEntry.amount), 0)) \
                 .filter_by(entry_type=entry_type).scalar()

    revenue = total("sale")
    cogs = total("cogs")
    purchases = total("purchase")
    payroll = db.query(func.coalesce(func.sum(models.Employee.salary), 0)).scalar()
    vat_collected = db.query(func.coalesce(func.sum(models.Invoice.vat_amount), 0)).scalar()

    return {
        "revenue": round(revenue, 2),                      # إجمالي المبيعات (شامل الضريبة)
        "vat_collected": round(vat_collected, 2),          # الضريبة المحصلة
        "cogs": round(cogs, 2),                            # تكلفة البضاعة المباعة
        "purchases": round(purchases, 2),                  # المشتريات المستلمة
        "monthly_payroll": round(payroll, 2),              # الرواتب الشهرية
        "gross_profit": round(revenue - vat_collected - cogs, 2),  # الربح الإجمالي
        "invoices_count": db.query(models.Invoice).count(),
        "journal_entries_count": db.query(models.JournalEntry).count(),
    }


@router.get("/invoices/{invoice_id}/print", response_class=HTMLResponse)
def printable_invoice(invoice_id: int, db: Session = Depends(get_db)):
    """فاتورة قابلة للطباعة (اطبعها من المتصفح أو احفظها PDF بـ Ctrl+P)."""
    inv = db.get(models.Invoice, invoice_id)
    if not inv:
        raise HTTPException(status_code=404, detail="الفاتورة غير موجودة")
    order = inv.sales_order
    product = db.get(models.Product, order.product_id)
    esc = html.escape

    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl"><head><meta charset="utf-8">
<title>فاتورة {esc(inv.number)}</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 700px; margin: 40px auto; color: #111; padding: 0 16px; }}
  header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 3px solid #111; padding-bottom: 14px; }}
  h1 {{ font-size: 22px; }} .muted {{ color: #666; font-size: 13px; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 24px; }}
  th, td {{ border: 1px solid #ccc; padding: 10px; text-align: right; font-size: 14px; }}
  th {{ background: #f4f4f4; }}
  .totals {{ margin-top: 18px; margin-right: auto; width: 280px; }}
  .totals div {{ display: flex; justify-content: space-between; padding: 6px 0; font-size: 14px; }}
  .totals .grand {{ border-top: 2px solid #111; font-weight: 700; font-size: 17px; }}
  .print-btn {{ margin-top: 30px; padding: 10px 26px; font-size: 15px; cursor: pointer; }}
  @media print {{ .print-btn {{ display: none; }} }}
</style></head><body>
<header>
  <div><h1>🏭 Smart Factory ERP</h1><div class="muted">فاتورة ضريبية مبسطة</div></div>
  <div style="text-align:left">
    <div style="font-size:18px;font-weight:700">{esc(inv.number)}</div>
    <div class="muted">{inv.issued_at.strftime('%Y-%m-%d %H:%M')}</div>
  </div>
</header>
<p style="margin-top:20px"><strong>العميل:</strong> {esc(order.customer_name)}</p>
<table>
  <thead><tr><th>الصنف</th><th>الكمية</th><th>سعر الوحدة</th><th>الإجمالي</th></tr></thead>
  <tbody><tr>
    <td>{esc(product.name)}</td>
    <td>{order.quantity:g}</td>
    <td>{order.unit_price:,.2f}</td>
    <td>{inv.subtotal:,.2f}</td>
  </tr></tbody>
</table>
<div class="totals">
  <div><span>الإجمالي قبل الضريبة</span><span>{inv.subtotal:,.2f}</span></div>
  <div><span>ضريبة القيمة المضافة ({inv.vat_rate:.0%})</span><span>{inv.vat_amount:,.2f}</span></div>
  <div class="grand"><span>الإجمالي المستحق</span><span>{inv.total:,.2f}</span></div>
</div>
<button class="print-btn" onclick="print()">🖨 طباعة / حفظ PDF</button>
</body></html>"""

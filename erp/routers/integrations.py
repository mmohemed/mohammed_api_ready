# =========================================
# التكامل مع الأنظمة والأجهزة الخارجية
# - مفاتيح API (يديرها admin) تُرسل في ترويسة X-API-Key
# - نقطة استقبال أجهزة البصمة/الحضور
# - باركود QR للمنتجات
# =========================================
import hashlib
import io
import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from .. import models
from ..auth import require_admin
from ..database import get_db
from .hr import _record_attendance

router = APIRouter(prefix="/integrations", tags=["التكامل الخارجي"])


# ---------- مفاتيح API ----------
def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def require_api_key(x_api_key: str = Header(default="", alias="X-API-Key"),
                    db: Session = Depends(get_db)) -> models.ApiKey:
    if not x_api_key:
        raise HTTPException(status_code=401, detail="أرسل مفتاح التكامل في ترويسة X-API-Key")
    record = db.query(models.ApiKey).filter_by(key_hash=_hash_key(x_api_key), active=1).first()
    if not record:
        raise HTTPException(status_code=401, detail="مفتاح تكامل غير صالح أو موقوف")
    return record


@router.post("/keys")
def create_api_key(body: dict, db: Session = Depends(get_db),
                   _: object = Depends(require_admin)):
    """إنشاء مفتاح تكامل جديد — المفتاح يظهر مرة واحدة فقط، احفظه."""
    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="أدخل اسمًا للمفتاح (مثال: جهاز بصمة البوابة)")
    key = "erp_" + secrets.token_hex(20)
    db.add(models.ApiKey(name=name, key_hash=_hash_key(key), prefix=key[:12]))
    db.commit()
    return {"name": name, "api_key": key,
            "warning": "⚠️ احفظ المفتاح الآن — لن يُعرض مرة أخرى"}


@router.get("/keys")
def list_api_keys(db: Session = Depends(get_db), _: object = Depends(require_admin)):
    return [
        {"id": k.id, "name": k.name, "prefix": k.prefix + "…",
         "active": bool(k.active), "created_at": k.created_at}
        for k in db.query(models.ApiKey).all()
    ]


@router.delete("/keys/{key_id}")
def revoke_api_key(key_id: int, db: Session = Depends(get_db),
                   _: object = Depends(require_admin)):
    key = db.get(models.ApiKey, key_id)
    if not key:
        raise HTTPException(status_code=404, detail="المفتاح غير موجود")
    key.active = 0
    db.commit()
    return {"message": f"أُوقف المفتاح «{key.name}»"}


# ---------- أجهزة البصمة / الحضور ----------
@router.post("/attendance")
def device_attendance(body: dict, db: Session = Depends(get_db),
                      device: models.ApiKey = Depends(require_api_key)):
    """نقطة استقبال أجهزة البصمة وقارئات البطاقات.

    الحمولة: {"badge_code": "1001", "direction": "in"|"out", "timestamp": "2026-07-05T08:00:00" (اختياري)}
    يدعم أيضًا employee_id بدل badge_code.
    """
    direction = body.get("direction")
    if direction not in ("in", "out"):
        raise HTTPException(status_code=400, detail="direction يجب أن يكون in أو out")

    employee = None
    if body.get("badge_code"):
        employee = db.query(models.Employee).filter_by(badge_code=str(body["badge_code"])).first()
    elif body.get("employee_id"):
        employee = db.get(models.Employee, int(body["employee_id"]))
    if not employee:
        raise HTTPException(status_code=404, detail="لا يوجد موظف بهذا الرقم/البطاقة")

    timestamp = datetime.utcnow()
    if body.get("timestamp"):
        try:
            timestamp = datetime.fromisoformat(str(body["timestamp"]))
        except ValueError:
            raise HTTPException(status_code=400, detail="صيغة timestamp غير صالحة (ISO 8601)")

    return _record_attendance(db, employee, direction, timestamp, source="device")


# ---------- باركود QR ----------
@router.get("/qrcode/product/{product_id}")
def product_qrcode(product_id: int, db: Session = Depends(get_db)):
    """صورة QR للمنتج (تحمل رمز SKU) — للطباعة ولصقها على الأصناف."""
    import qrcode

    product = db.get(models.Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="المنتج غير موجود")
    img = qrcode.make(product.sku, box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return Response(content=buf.getvalue(), media_type="image/png",
                    headers={"Content-Disposition": f'inline; filename="{product.sku}.png"'})

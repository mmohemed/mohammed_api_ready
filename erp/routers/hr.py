# =========================================
# الموارد البشرية: الحضور والانصراف
# يدويًا من الواجهة أو تلقائيًا من أجهزة البصمة (عبر /integrations)
# =========================================
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models
from ..auth import require_department
from ..database import get_db

router = APIRouter(prefix="/hr", tags=["الموارد البشرية"])


def _record_attendance(db: Session, employee: models.Employee, direction: str,
                       timestamp: datetime, source: str) -> dict:
    """منطق مشترك لتسجيل حضور/انصراف (يدوي أو من جهاز)."""
    open_record = (
        db.query(models.AttendanceRecord)
        .filter_by(employee_id=employee.id, check_out=None)
        .order_by(models.AttendanceRecord.check_in.desc())
        .first()
    )
    if direction == "in":
        if open_record:
            raise HTTPException(status_code=400, detail=f"{employee.name} مسجّل حضور بالفعل ولم يسجل انصرافًا")
        db.add(models.AttendanceRecord(employee_id=employee.id, check_in=timestamp, source=source))
        message = f"سُجّل حضور {employee.name}"
    else:
        if not open_record:
            raise HTTPException(status_code=400, detail=f"لا يوجد حضور مفتوح لـ {employee.name}")
        if timestamp <= open_record.check_in:
            raise HTTPException(status_code=400, detail="وقت الانصراف قبل وقت الحضور")
        open_record.check_out = timestamp
        message = f"سُجّل انصراف {employee.name}"
    db.commit()
    return {"message": message, "employee_id": employee.id, "direction": direction}


@router.post("/attendance/{employee_id}/{direction}")
def manual_attendance(employee_id: int, direction: str, db: Session = Depends(get_db),
                      _: object = Depends(require_department("الموارد البشرية"))):
    """تسجيل حضور (in) أو انصراف (out) يدويًا من الواجهة."""
    if direction not in ("in", "out"):
        raise HTTPException(status_code=400, detail="الاتجاه يجب أن يكون in أو out")
    employee = db.get(models.Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="الموظف غير موجود")
    return _record_attendance(db, employee, direction, datetime.utcnow(), source="manual")


@router.get("/attendance")
def list_attendance(day: str | None = Query(default=None, description="YYYY-MM-DD، افتراضي اليوم"),
                    db: Session = Depends(get_db)):
    """سجل الحضور ليوم محدد مع حالة كل موظف."""
    try:
        target = date.fromisoformat(day) if day else datetime.utcnow().date()
    except ValueError:
        raise HTTPException(status_code=400, detail="صيغة التاريخ: YYYY-MM-DD")

    records = (
        db.query(models.AttendanceRecord)
        .filter(func.date(models.AttendanceRecord.check_in) == target.isoformat())
        .all()
    )
    by_employee = {r.employee_id: r for r in sorted(records, key=lambda r: r.check_in)}
    result = []
    for employee in db.query(models.Employee).all():
        record = by_employee.get(employee.id)
        hours = None
        if record and record.check_out:
            hours = round((record.check_out - record.check_in).total_seconds() / 3600, 2)
        result.append({
            "employee_id": employee.id,
            "name": employee.name,
            "department": employee.department,
            "badge_code": employee.badge_code,
            "check_in": record.check_in if record else None,
            "check_out": record.check_out if record else None,
            "hours": hours,
            "source": record.source if record else None,
            "status": ("✅ حاضر" if record and not record.check_out
                       else "🏠 انصرف" if record else "✖ غائب"),
        })
    return {"date": target.isoformat(), "records": result,
            "present": sum(1 for r in result if r["check_in"])}

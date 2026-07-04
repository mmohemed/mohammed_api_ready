# =========================================
# الآلات + قراءات الحساسات + الصيانة التنبؤية
# =========================================
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..ai.predictive_maintenance import predict_failure
from ..database import get_db

router = APIRouter(prefix="/machines", tags=["الآلات والصيانة"])


@router.post("", response_model=schemas.MachineOut)
def create_machine(machine: schemas.MachineCreate, db: Session = Depends(get_db)):
    row = models.Machine(**machine.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("", response_model=list[schemas.MachineOut])
def list_machines(db: Session = Depends(get_db)):
    return db.query(models.Machine).all()


@router.post("/{machine_id}/readings", response_model=schemas.SensorReadingOut)
def add_reading(machine_id: int, reading: schemas.SensorReadingCreate, db: Session = Depends(get_db)):
    if not db.get(models.Machine, machine_id):
        raise HTTPException(status_code=404, detail="الآلة غير موجودة")
    row = models.SensorReading(machine_id=machine_id, **reading.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/{machine_id}/predict-failure")
def machine_failure_prediction(machine_id: int, db: Session = Depends(get_db)):
    """🤖 الصيانة التنبؤية: احتمال العطل بناءً على آخر قراءة حساسات."""
    machine = db.get(models.Machine, machine_id)
    if not machine:
        raise HTTPException(status_code=404, detail="الآلة غير موجودة")

    reading = (
        db.query(models.SensorReading)
        .filter_by(machine_id=machine_id)
        .order_by(models.SensorReading.recorded_at.desc())
        .first()
    )
    if not reading:
        raise HTTPException(status_code=400, detail="لا توجد قراءات حساسات لهذه الآلة بعد")

    prediction = predict_failure(
        reading.temperature, reading.vibration, reading.pressure, reading.running_hours
    )
    return {
        "machine_id": machine_id,
        "machine_name": machine.name,
        "latest_reading": {
            "temperature": reading.temperature,
            "vibration": reading.vibration,
            "pressure": reading.pressure,
            "running_hours": reading.running_hours,
            "recorded_at": reading.recorded_at,
        },
        **prediction,
    }


@router.post("/{machine_id}/maintenance-done", response_model=schemas.MachineOut)
def mark_maintenance_done(machine_id: int, db: Session = Depends(get_db)):
    """تسجيل إتمام صيانة: يعيد الآلة للعمل ويصفّر ساعات التشغيل مرجعيًا."""
    machine = db.get(models.Machine, machine_id)
    if not machine:
        raise HTTPException(status_code=404, detail="الآلة غير موجودة")
    machine.status = "working"
    machine.last_maintenance = datetime.utcnow()
    db.commit()
    db.refresh(machine)
    return machine

# =========================================
# الموظفون والموارد البشرية
# =========================================
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import require_department
from ..database import get_db

router = APIRouter(prefix="/employees", tags=["الموظفون"])


@router.post("", response_model=schemas.EmployeeOut)
def create_employee(employee: schemas.EmployeeCreate, db: Session = Depends(get_db),
                 _: object = Depends(require_department("الموارد البشرية"))):
    row = models.Employee(**employee.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("", response_model=list[schemas.EmployeeOut])
def list_employees(db: Session = Depends(get_db)):
    return db.query(models.Employee).all()


@router.put("/{employee_id}", response_model=schemas.EmployeeOut)
def update_employee(employee_id: int, changes: schemas.EmployeeUpdate, db: Session = Depends(get_db),
                    _: object = Depends(require_department("الموارد البشرية"))):
    employee = db.get(models.Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="الموظف غير موجود")
    for field, value in changes.model_dump(exclude_none=True).items():
        setattr(employee, field, value)
    db.commit()
    db.refresh(employee)
    return employee


@router.delete("/{employee_id}")
def delete_employee(employee_id: int, db: Session = Depends(get_db),
                 _: object = Depends(require_department("الموارد البشرية"))):
    employee = db.get(models.Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="الموظف غير موجود")
    db.delete(employee)
    db.commit()
    return {"message": "تم حذف الموظف بنجاح"}

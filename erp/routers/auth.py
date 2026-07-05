# =========================================
# تسجيل الدخول وإدارة المستخدمين
# =========================================
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import (
    create_token,
    get_current_user,
    get_optional_user,
    hash_password,
    require_admin,
    verify_password,
)
from ..database import get_db

router = APIRouter(prefix="/auth", tags=["المصادقة والمستخدمون"])


@router.post("/login", response_model=schemas.TokenResponse)
def login(body: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter_by(username=body.username).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="اسم المستخدم أو كلمة المرور غير صحيحة")
    return schemas.TokenResponse(
        access_token=create_token(user.id, user.username, user.role),
        role=user.role,
        username=user.username,
    )


@router.post("/register", response_model=schemas.UserOut)
def register(
    body: schemas.UserCreate,
    db: Session = Depends(get_db),
    current: models.User | None = Depends(get_optional_user),
):
    """إنشاء مستخدم.

    - أول مستخدم في النظام يُنشأ بدون مصادقة ويصبح admin تلقائيًا (Bootstrap).
    - بعد ذلك، إنشاء المستخدمين لمدير النظام فقط.
    """
    users_exist = db.query(models.User).count() > 0
    if users_exist:
        if current is None:
            raise HTTPException(status_code=401, detail="مطلوب تسجيل الدخول بحساب admin")
        if current.role != "admin":
            raise HTTPException(status_code=403, detail="إنشاء المستخدمين لمدير النظام فقط")
    if db.query(models.User).filter_by(username=body.username).first():
        raise HTTPException(status_code=400, detail="اسم المستخدم مستخدم بالفعل")

    role = body.role if users_exist else "admin"
    user = models.User(
        username=body.username,
        full_name=body.full_name,
        password_hash=hash_password(body.password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(get_current_user)):
    return user


@router.get("/users", response_model=list[schemas.UserOut])
def list_users(db: Session = Depends(get_db), _: models.User = Depends(require_admin)):
    return db.query(models.User).all()

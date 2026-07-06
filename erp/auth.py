# =========================================
# المصادقة والصلاحيات
# - تجزئة كلمات المرور: PBKDF2 (مكتبة بايثون القياسية)
# - رموز دخول موقّعة HMAC-SHA256 مع تاريخ انتهاء
# - الأدوار: admin (كل شيء) / manager (قراءة + كتابة) / viewer (قراءة فقط)
# =========================================
import base64
import hashlib
import hmac
import json
import os
import secrets
import time

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from . import models
from .database import get_db

# مخطط الأمان: يجعل زر Authorize يظهر في صفحة /docs
bearer_scheme = HTTPBearer(auto_error=False, description="الصق access_token من رد /auth/login")

# ⚠️ في الإنتاج عرّف ERP_SECRET_KEY في متغيرات البيئة
SECRET_KEY = os.environ.get("ERP_SECRET_KEY", "dev-secret-change-me").encode()
TOKEN_TTL_SECONDS = 12 * 3600  # صلاحية الرمز: 12 ساعة

WRITER_ROLES = {"admin", "manager"}

DEPARTMENTS = [
    "الإدارة", "المبيعات", "المشتريات", "المخازن",
    "الإنتاج", "الجودة", "المحاسبة", "الموارد البشرية",
]


# ---------- كلمات المرور ----------
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, expected = stored.split("$", 1)
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000)
    return hmac.compare_digest(digest.hex(), expected)


# ---------- الرموز (Tokens) ----------
def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def create_token(user_id: int, username: str, role: str) -> str:
    payload = {"uid": user_id, "sub": username, "role": role, "exp": int(time.time()) + TOKEN_TTL_SECONDS}
    body = _b64(json.dumps(payload).encode())
    signature = _b64(hmac.new(SECRET_KEY, body.encode(), hashlib.sha256).digest())
    return f"{body}.{signature}"


def decode_token(token: str) -> dict:
    try:
        body, signature = token.split(".", 1)
        expected = _b64(hmac.new(SECRET_KEY, body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise ValueError("bad signature")
        payload = json.loads(_unb64(body))
        if payload["exp"] < time.time():
            raise ValueError("expired")
        return payload
    except (ValueError, KeyError, json.JSONDecodeError):
        raise HTTPException(status_code=401, detail="رمز الدخول غير صالح أو منتهي الصلاحية")


# ---------- Dependencies ----------
def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="مطلوب تسجيل الدخول: أرسل الرمز في ترويسة Authorization: Bearer <token>",
        )
    payload = decode_token(credentials.credentials.strip())
    user = db.get(models.User, payload["uid"])
    if not user:
        raise HTTPException(status_code=401, detail="المستخدم غير موجود")
    return user


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> models.User | None:
    """مثل get_current_user لكن يعيد None بدل 401 عند غياب الرمز.

    يُستخدم في المسارات التي تتصرف باختلاف وجود مستخدم (مثل Bootstrap أول admin)."""
    if credentials is None:
        return None
    payload = decode_token(credentials.credentials.strip())
    return db.get(models.User, payload["uid"])


def require_writer(user: models.User = Depends(get_current_user)) -> models.User:
    """يسمح بعمليات الكتابة العامة لمديري النظام والمشرفين فقط."""
    if user.role not in WRITER_ROLES:
        raise HTTPException(status_code=403, detail="ليست لديك صلاحية كتابة عامة")
    return user


def require_department(department: str):
    """صلاحية كتابة على مستوى القسم:

    - admin و manager: يكتبون في كل الأقسام
    - user: يكتب في قسمه فقط (أو إن كان قسمه «الإدارة»)
    - viewer: قراءة فقط
    """
    def checker(user: models.User = Depends(get_current_user)) -> models.User:
        if user.role in WRITER_ROLES:
            return user
        if user.role == "user" and user.department in (department, "الإدارة"):
            return user
        raise HTTPException(
            status_code=403,
            detail=f"هذه العملية مخصصة لقسم «{department}» (قسمك: {user.department}, دورك: {user.role})",
        )
    return checker


def require_admin(user: models.User = Depends(get_current_user)) -> models.User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="هذه العملية لمدير النظام فقط")
    return user

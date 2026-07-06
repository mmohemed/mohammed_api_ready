# =========================================
# مخططات Pydantic (المدخلات والمخرجات)
# =========================================
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------- المنتجات / المخزون ----------
class ProductCreate(BaseModel):
    name: str
    sku: str
    category: str = "عام"
    product_type: str = Field(default="finished", pattern="^(finished|raw)$",
                              description="finished منتج نهائي / raw مادة خام")
    unit: str = "قطعة"
    quantity: float = 0
    reorder_point: float = 10
    unit_cost: float = 0
    unit_price: float = 0


class ProductOut(ProductCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ProductUpdate(BaseModel):
    """تحديث بيانات منتج — كل الحقول اختيارية (الكمية تُعدّل عبر /adjust)"""
    name: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    reorder_point: Optional[float] = None
    unit_cost: Optional[float] = None
    unit_price: Optional[float] = None


class StockAdjust(BaseModel):
    change: float = Field(description="التغيير في الكمية: موجب للإضافة وسالب للسحب")
    reason: str = "تسوية مخزون"


class BOMItemCreate(BaseModel):
    component_id: int = Field(description="رقم المادة الخام")
    quantity_per_unit: float = Field(gt=0, description="الكمية المستهلكة لكل وحدة منتجة")


# ---------- الآلات والصيانة ----------
class MachineCreate(BaseModel):
    name: str
    machine_type: str = "خط إنتاج"
    status: str = "working"


class MachineOut(MachineCreate):
    id: int
    installed_at: datetime
    last_maintenance: datetime

    class Config:
        from_attributes = True


class MachineUpdate(BaseModel):
    name: Optional[str] = None
    machine_type: Optional[str] = None
    status: Optional[str] = Field(default=None, pattern="^(working|maintenance|stopped)$")


class SensorReadingCreate(BaseModel):
    temperature: float = Field(description="درجة الحرارة بالمئوية")
    vibration: float = Field(description="الاهتزاز ملم/ثانية")
    pressure: float = Field(description="الضغط بالبار")
    running_hours: float = Field(description="ساعات التشغيل منذ آخر صيانة")


class SensorReadingOut(SensorReadingCreate):
    id: int
    machine_id: int
    recorded_at: datetime

    class Config:
        from_attributes = True


# ---------- الإنتاج ----------
class ProductionOrderCreate(BaseModel):
    product_id: int
    machine_id: Optional[int] = None
    planned_quantity: float


class ProductionReport(BaseModel):
    produced_quantity: float
    defective_quantity: float = 0


class ProductionOrderOut(BaseModel):
    id: int
    product_id: int
    machine_id: Optional[int]
    sales_order_id: Optional[int]
    planned_quantity: float
    produced_quantity: float
    defective_quantity: float
    status: str
    source: str
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


# ---------- المبيعات ----------
class SalesOrderCreate(BaseModel):
    product_id: int
    customer_name: str = "عميل"
    quantity: float
    unit_price: Optional[float] = None  # إن لم يُحدد يؤخذ سعر المنتج


class SalesOrderOut(BaseModel):
    id: int
    product_id: int
    customer_name: str
    quantity: float
    unit_price: float
    status: str
    ordered_at: datetime
    delivered_at: Optional[datetime]

    class Config:
        from_attributes = True


# ---------- الموردون والمشتريات ----------
class SupplierCreate(BaseModel):
    name: str
    phone: str = ""
    email: str = ""
    address: str = ""


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None


class SupplierOut(SupplierCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class PurchaseOrderCreate(BaseModel):
    supplier_id: int
    product_id: int
    quantity: float = Field(gt=0)
    unit_cost: Optional[float] = Field(default=None, description="إن لم يُحدد تؤخذ تكلفة المنتج")


class PurchaseApprove(BaseModel):
    """اعتماد طلب شراء تلقائي: تعيين المورد (مع تعديل اختياري للكمية والتكلفة)"""
    supplier_id: int
    unit_cost: Optional[float] = None
    quantity: Optional[float] = Field(default=None, gt=0)


class PurchaseOrderOut(BaseModel):
    id: int
    supplier_id: Optional[int]
    product_id: int
    quantity: float
    unit_cost: float
    status: str
    source: str
    note: str
    ordered_at: datetime
    received_at: Optional[datetime]

    class Config:
        from_attributes = True


# ---------- الموظفون ----------
class EmployeeCreate(BaseModel):
    name: str
    role: str = "عامل إنتاج"
    department: str = "الإنتاج"
    salary: float = 0
    badge_code: Optional[str] = Field(default=None, description="رقم البطاقة/البصمة لأجهزة الحضور")


class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    salary: Optional[float] = None
    badge_code: Optional[str] = None


class EmployeeOut(EmployeeCreate):
    id: int
    hired_at: datetime

    class Config:
        from_attributes = True


# ---------- المستخدمون والمصادقة ----------
class UserCreate(BaseModel):
    username: str
    password: str = Field(min_length=6, description="6 أحرف على الأقل")
    full_name: str = ""
    role: str = Field(default="viewer", pattern="^(admin|manager|user|viewer)$",
                      description="admin كل شيء / manager كتابة عامة / user كتابة في قسمه / viewer قراءة")
    department: str = "الإدارة"


class UserOut(BaseModel):
    id: int
    username: str
    full_name: str
    role: str
    department: str
    created_at: datetime

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str


# ---------- الذكاء الاصطناعي ----------
class AssistantQuestion(BaseModel):
    question: str = Field(description="سؤال بالعربية عن حالة المصنع")

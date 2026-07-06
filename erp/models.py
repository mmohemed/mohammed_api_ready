# =========================================
# نماذج قاعدة البيانات (جداول ERP المصنع)
# =========================================
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    """مستخدمو النظام.

    الأدوار: admin (كل شيء) / manager (كتابة في كل الأقسام) /
             user (كتابة في قسمه فقط) / viewer (قراءة فقط)
    الأقسام: الإدارة، المبيعات، المشتريات، المخازن، الإنتاج، الجودة، المحاسبة، الموارد البشرية
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    full_name = Column(String, default="")
    password_hash = Column(String, nullable=False)
    role = Column(String, default="viewer")          # admin / manager / user / viewer
    department = Column(String, default="الإدارة")
    created_at = Column(DateTime, default=datetime.utcnow)


class Product(Base):
    """المنتجات / أصناف المخزون"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    sku = Column(String, unique=True, nullable=False, index=True)
    category = Column(String, default="عام")
    product_type = Column(String, default="finished")  # finished (منتج نهائي) / raw (مادة خام)
    unit = Column(String, default="قطعة")
    quantity = Column(Float, default=0)              # الكمية الحالية بالمخزون
    reorder_point = Column(Float, default=10)        # حد إعادة الطلب
    unit_cost = Column(Float, default=0)             # تكلفة الوحدة
    unit_price = Column(Float, default=0)            # سعر البيع
    created_at = Column(DateTime, default=datetime.utcnow)

    sales = relationship("SalesOrder", back_populates="product")
    production_orders = relationship("ProductionOrder", back_populates="product")


class Machine(Base):
    """آلات وخطوط الإنتاج"""
    __tablename__ = "machines"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    machine_type = Column(String, default="خط إنتاج")
    status = Column(String, default="working")       # working / maintenance / stopped
    installed_at = Column(DateTime, default=datetime.utcnow)
    last_maintenance = Column(DateTime, default=datetime.utcnow)

    readings = relationship("SensorReading", back_populates="machine")
    production_orders = relationship("ProductionOrder", back_populates="machine")


class SensorReading(Base):
    """قراءات حساسات الآلات (حرارة، اهتزاز، ساعات تشغيل...)"""
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, index=True)
    machine_id = Column(Integer, ForeignKey("machines.id"), nullable=False)
    temperature = Column(Float, nullable=False)      # درجة الحرارة (مئوية)
    vibration = Column(Float, nullable=False)        # الاهتزاز (ملم/ثانية)
    pressure = Column(Float, nullable=False)         # الضغط (بار)
    running_hours = Column(Float, nullable=False)    # ساعات التشغيل منذ آخر صيانة
    recorded_at = Column(DateTime, default=datetime.utcnow)

    machine = relationship("Machine", back_populates="readings")


class ProductionOrder(Base):
    """أوامر الإنتاج"""
    __tablename__ = "production_orders"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    machine_id = Column(Integer, ForeignKey("machines.id"), nullable=True)
    sales_order_id = Column(Integer, ForeignKey("sales_orders.id"), nullable=True)  # إن أُنشئ تلقائيًا من طلب بيع
    planned_quantity = Column(Float, nullable=False)
    produced_quantity = Column(Float, default=0)
    defective_quantity = Column(Float, default=0)    # الوحدات المعيبة (للجودة)
    status = Column(String, default="planned")       # planned / in_progress / completed / cancelled
    source = Column(String, default="manual")        # manual / auto
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    product = relationship("Product", back_populates="production_orders")
    machine = relationship("Machine", back_populates="production_orders")


class SalesOrder(Base):
    """طلبات البيع (تُستخدم أيضًا للتنبؤ بالطلب)"""
    __tablename__ = "sales_orders"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    customer_name = Column(String, default="عميل")
    quantity = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=False)
    # confirmed (مخصوم من المخزون) / pending_production (بانتظار الإنتاج) / delivered / cancelled
    status = Column(String, default="confirmed")
    ordered_at = Column(DateTime, default=datetime.utcnow)
    delivered_at = Column(DateTime, nullable=True)

    product = relationship("Product", back_populates="sales")


class BOMItem(Base):
    """مكونات المنتج (Bill of Materials): كم يحتاج المنتج النهائي من كل مادة خام"""
    __tablename__ = "bom_items"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)     # المنتج النهائي
    component_id = Column(Integer, ForeignKey("products.id"), nullable=False)   # المادة الخام
    quantity_per_unit = Column(Float, nullable=False)                           # الكمية لكل وحدة منتجة

    product = relationship("Product", foreign_keys=[product_id])
    component = relationship("Product", foreign_keys=[component_id])


class Invoice(Base):
    """فواتير البيع — تُصدر تلقائيًا عند تسليم طلب البيع"""
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    number = Column(String, unique=True, nullable=False)     # INV-00001
    sales_order_id = Column(Integer, ForeignKey("sales_orders.id"), nullable=False)
    subtotal = Column(Float, nullable=False)
    vat_rate = Column(Float, default=0.15)                   # ضريبة القيمة المضافة
    vat_amount = Column(Float, nullable=False)
    total = Column(Float, nullable=False)
    issued_at = Column(DateTime, default=datetime.utcnow)

    sales_order = relationship("SalesOrder")


class JournalEntry(Base):
    """القيود المحاسبية — تُسجل تلقائيًا مع كل حركة مالية"""
    __tablename__ = "journal_entries"

    id = Column(Integer, primary_key=True, index=True)
    entry_type = Column(String, nullable=False)      # sale / cogs / purchase / salary ...
    description = Column(String, nullable=False)
    debit_account = Column(String, nullable=False)   # الحساب المدين
    credit_account = Column(String, nullable=False)  # الحساب الدائن
    amount = Column(Float, nullable=False)
    reference = Column(String, default="")           # مرجع (رقم فاتورة/أمر)
    created_at = Column(DateTime, default=datetime.utcnow)


class Supplier(Base):
    """الموردون"""
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    phone = Column(String, default="")
    email = Column(String, default="")
    address = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    purchase_orders = relationship("PurchaseOrder", back_populates="supplier")


class PurchaseOrder(Base):
    """أوامر الشراء من الموردين"""
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)   # فارغ للطلبات التلقائية حتى يعتمدها قسم المشتريات
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    unit_cost = Column(Float, nullable=False)
    status = Column(String, default="ordered")       # requested (تلقائي بانتظار الاعتماد) / ordered / received / cancelled
    source = Column(String, default="manual")        # manual / auto
    note = Column(String, default="")
    ordered_at = Column(DateTime, default=datetime.utcnow)
    received_at = Column(DateTime, nullable=True)

    supplier = relationship("Supplier", back_populates="purchase_orders")
    product = relationship("Product")


class Employee(Base):
    """الموظفون والعمال"""
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    role = Column(String, default="عامل إنتاج")
    department = Column(String, default="الإنتاج")
    salary = Column(Float, default=0)
    hired_at = Column(DateTime, default=datetime.utcnow)

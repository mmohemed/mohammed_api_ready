# =========================================
# نماذج قاعدة البيانات (جداول ERP المصنع)
# =========================================
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    """مستخدمو النظام: admin / manager / viewer"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    full_name = Column(String, default="")
    password_hash = Column(String, nullable=False)
    role = Column(String, default="viewer")          # admin / manager / viewer
    created_at = Column(DateTime, default=datetime.utcnow)


class Product(Base):
    """المنتجات / أصناف المخزون"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    sku = Column(String, unique=True, nullable=False, index=True)
    category = Column(String, default="عام")
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
    planned_quantity = Column(Float, nullable=False)
    produced_quantity = Column(Float, default=0)
    defective_quantity = Column(Float, default=0)    # الوحدات المعيبة (للجودة)
    status = Column(String, default="planned")       # planned / in_progress / completed / cancelled
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
    status = Column(String, default="confirmed")     # confirmed / delivered / cancelled
    ordered_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="sales")


class Employee(Base):
    """الموظفون والعمال"""
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    role = Column(String, default="عامل إنتاج")
    department = Column(String, default="الإنتاج")
    salary = Column(Float, default=0)
    hired_at = Column(DateTime, default=datetime.utcnow)

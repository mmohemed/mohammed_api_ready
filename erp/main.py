# =========================================
# Smart Factory ERP - نظام ERP ذكي للمصانع
# مدعوم بالذكاء الاصطناعي:
#  🤖 صيانة تنبؤية للآلات
#  🤖 توقع الطلب واقتراحات إعادة الطلب
#  🤖 كشف شذوذ الجودة في الإنتاج
#  🤖 مساعد ذكي يجيب بالعربية
#
# التشغيل: uvicorn erp.main:app --reload
# الوثائق التفاعلية: http://localhost:8000/docs
# =========================================
import os

from fastapi import FastAPI
from fastapi.responses import FileResponse

from .ai.predictive_maintenance import get_model
from .database import Base, engine
from .routers import (
    accounting,
    auth,
    dashboard,
    employees,
    inventory,
    machines,
    production,
    purchases,
    sales,
)

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Smart Factory ERP 🏭",
    description=(
        "نظام تخطيط موارد ذكي للمصانع: مخزون، إنتاج، آلات وصيانة، مبيعات، موظفون — "
        "مع صيانة تنبؤية، توقع طلب، كشف شذوذ جودة، ومساعد ذكي بالعربية."
    ),
    version="1.0",
)


@app.on_event("startup")
def train_ai_models():
    # تدريب نموذج الصيانة التنبؤية مرة واحدة عند الإقلاع
    get_model()
    # استقبال قراءات الحساسات عبر MQTT (يعمل فقط عند تعريف ERP_MQTT_BROKER)
    from .iot.mqtt_ingest import start_mqtt_listener
    start_mqtt_listener()


app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(inventory.router)
app.include_router(machines.router)
app.include_router(production.router)
app.include_router(sales.router)
app.include_router(purchases.router)
app.include_router(accounting.router)
app.include_router(employees.router)


@app.get("/", include_in_schema=False)
def root():
    """تطبيق التشغيل الكامل: تسجيل دخول + إدارة كل الأقسام"""
    return FileResponse(os.path.join(STATIC_DIR, "app.html"))


@app.get("/classic", include_in_schema=False)
def classic_dashboard():
    """لوحة العرض القديمة (قراءة فقط)"""
    return FileResponse(os.path.join(STATIC_DIR, "dashboard.html"))


@app.get("/api/info")
def api_info():
    return {
        "message": "مرحبًا بك في Smart Factory ERP 🏭 — نظام ERP ذكي للمصانع",
        "dashboard": "/",
        "docs": "/docs",
        "auth": "POST /auth/login — تسجيل الدخول (عمليات الكتابة تتطلب دور admin أو manager)",
        "modules": {
            "dashboard": "GET /dashboard — مؤشرات المصنع",
            "inventory": "GET /inventory/products — المخزون والتنبيهات الذكية",
            "machines": "GET /machines — الآلات والصيانة التنبؤية",
            "production": "GET /production/orders — الإنتاج وكشف شذوذ الجودة",
            "sales": "GET /sales/orders — المبيعات وتوقع الطلب",
            "employees": "GET /employees — الموظفون",
            "assistant": "POST /ai/assistant — المساعد الذكي بالعربية (Claude عند تعريف ANTHROPIC_API_KEY)",
            "insights": "GET /ai/insights — تقرير الرؤى والتوصيات المرتبة بالأولوية",
        },
    }

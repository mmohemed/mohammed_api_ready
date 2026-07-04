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
from fastapi import FastAPI

from .ai.predictive_maintenance import get_model
from .database import Base, engine
from .routers import dashboard, employees, inventory, machines, production, sales

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


app.include_router(dashboard.router)
app.include_router(inventory.router)
app.include_router(machines.router)
app.include_router(production.router)
app.include_router(sales.router)
app.include_router(employees.router)


@app.get("/")
def root():
    return {
        "message": "مرحبًا بك في Smart Factory ERP 🏭 — نظام ERP ذكي للمصانع",
        "docs": "/docs",
        "modules": {
            "dashboard": "GET /dashboard — مؤشرات المصنع",
            "inventory": "GET /inventory/products — المخزون والتنبيهات الذكية",
            "machines": "GET /machines — الآلات والصيانة التنبؤية",
            "production": "GET /production/orders — الإنتاج وكشف شذوذ الجودة",
            "sales": "GET /sales/orders — المبيعات وتوقع الطلب",
            "employees": "GET /employees — الموظفون",
            "assistant": "POST /ai/assistant — المساعد الذكي بالعربية",
        },
    }

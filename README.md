# 🏭 Smart Factory ERP — نظام ERP ذكي للمصانع

نظام تخطيط موارد مؤسسات (ERP) مخصص للمصانع، مبني بـ **FastAPI + SQLAlchemy + scikit-learn**، مع أربع قدرات ذكاء اصطناعي مدمجة وواجهة عربية بالكامل.

## ✨ الوحدات

| الوحدة | الوصف |
|---|---|
| 📦 المخزون | إدارة المنتجات والكميات، تنبيهات نفاد المخزون، اقتراحات إعادة طلب ذكية |
| ⚙️ الآلات والصيانة | تسجيل الآلات وقراءات الحساسات (حرارة، اهتزاز، ضغط، ساعات تشغيل) |
| 🏗️ الإنتاج والجودة | أوامر إنتاج، تسجيل المنتج والمعيب، إضافة الصافي للمخزون تلقائيًا |
| 💰 المبيعات | طلبات بيع مع خصم تلقائي من المخزون ومنع البيع فوق المتاح |
| 👥 الموظفون | سجل الموظفين والأقسام والرواتب |
| 📊 لوحة التحكم | مؤشرات KPIs للمصنع كاملًا في طلب واحد |

## 🤖 قدرات الذكاء الاصطناعي

1. **صيانة تنبؤية** — `GET /machines/{id}/predict-failure`
   نموذج Random Forest يتوقع احتمال عطل الآلة من آخر قراءة حساسات، مع مستوى الخطر وتوصية صيانة بالعربية.
2. **توقع الطلب** — `GET /sales/forecast/{product_id}?days_ahead=30`
   انحدار خطي على تاريخ المبيعات يتوقع الطلب القادم ويحدد الاتجاه (ازدياد/انخفاض/استقرار).
3. **اقتراحات إعادة الطلب** — `GET /inventory/alerts`
   يدمج توقع الطلب مع حد إعادة الطلب ليقترح الكمية المناسبة قبل نفاد المخزون.
4. **كشف شذوذ الجودة** — `GET /production/quality/anomalies`
   Isolation Forest يرصد أوامر الإنتاج ذات نسب العيوب أو الإنجاز غير الطبيعية.
5. **مساعد ذكي بالعربية** — `POST /ai/assistant`
   اسأل: «كيف حال المخزون؟» أو «كم إيرادات المبيعات؟» ويجيب من بيانات المصنع الفعلية.

## 🚀 التشغيل

```bash
# 1) تثبيت المتطلبات
pip install -r requirements.txt

# 2) (اختياري) تعبئة بيانات تجريبية: منتجات، آلات، 90 يوم مبيعات، أوامر إنتاج
python -m erp.seed

# 3) تشغيل الخادم
uvicorn erp.main:app --reload

# الوثائق التفاعلية (Swagger)
# http://localhost:8000/docs
```

## 🧪 أمثلة سريعة

```bash
# مؤشرات المصنع
curl http://localhost:8000/dashboard

# احتمال عطل الآلة رقم 2
curl http://localhost:8000/machines/2/predict-failure

# توقع الطلب على المنتج رقم 1 لثلاثين يومًا
curl "http://localhost:8000/sales/forecast/1?days_ahead=30"

# المساعد الذكي
curl -X POST http://localhost:8000/ai/assistant \
  -H "Content-Type: application/json" \
  -d '{"question": "كيف حال المخزون؟"}'
```

## 🗂️ بنية المشروع

```
erp/
├── main.py            # تطبيق FastAPI وتجميع المسارات
├── database.py        # إعداد SQLite + SQLAlchemy
├── models.py          # جداول قاعدة البيانات
├── schemas.py         # مخططات Pydantic
├── seed.py            # بيانات تجريبية
├── ai/
│   ├── predictive_maintenance.py   # الصيانة التنبؤية (Random Forest)
│   ├── demand_forecast.py          # توقع الطلب (Linear Regression)
│   ├── anomaly_detection.py        # كشف شذوذ الجودة (Isolation Forest)
│   └── assistant.py                # المساعد الذكي بالعربية
└── routers/
    ├── dashboard.py   # لوحة التحكم + المساعد
    ├── inventory.py   # المخزون
    ├── machines.py    # الآلات والصيانة
    ├── production.py  # الإنتاج والجودة
    ├── sales.py       # المبيعات
    └── employees.py   # الموظفون
```

> ملاحظة: يحتوي المستودع أيضًا على `main.py` في الجذر وهو API قديم لتشخيص أعطال السيارات، مستقل عن نظام الـ ERP.

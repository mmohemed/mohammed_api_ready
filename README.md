# 🏭 Smart Factory ERP — نظام ERP ذكي للمصانع

نظام تخطيط موارد مؤسسات (ERP) مخصص للمصانع، مبني بـ **FastAPI + SQLAlchemy + scikit-learn**، مع أربع قدرات ذكاء اصطناعي مدمجة وواجهة عربية بالكامل.

## ✨ الوحدات

| الوحدة | الوصف |
|---|---|
| 🖥️ لوحة تحكم مرئية | واجهة ويب عربية (RTL) على `/`: مؤشرات KPI، مخطط مبيعات تفاعلي، عدّادات خطر الآلات، تنبيهات المخزون، ومحادثة المساعد الذكي — بدون أي مكتبات خارجية |
| 🔐 المستخدمون والصلاحيات | تسجيل دخول برموز موقّعة، أدوار: `admin` / `manager` (قراءة وكتابة) / `viewer` (قراءة فقط) |
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
6. **مساعد Claude للأسئلة الحرة** 🧠 — نفس المسار `POST /ai/assistant`
   عند تعريف `ANTHROPIC_API_KEY` يتولى نموذج **Claude** الإجابة على أسئلة معقدة وتحليلات حرة
   («ما أكبر ثلاثة مخاطر هذا الأسبوع ولماذا؟») اعتمادًا على لقطة حية من بيانات المصنع.
   بدون المفتاح يعمل المساعد القاعدي تلقائيًا — لا يتعطل شيء.
7. **تقرير الرؤى الذكية** — `GET /ai/insights`
   يجمع كل إشارات الذكاء الاصطناعي (صيانة، مخزون، جودة، طلب) في قائمة توصيات
   واحدة مرتبة بالأولوية (🔴 حرج → 🔵 معلومة) — تقرير الصباح لمدير المصنع.
8. **إنترنت الأشياء (MQTT)** — استقبال قراءات الحساسات مباشرة من أجهزة المصنع:
   عرّف `ERP_MQTT_BROKER` (و`ERP_MQTT_PORT` اختياريًا) ويستمع النظام تلقائيًا للعنوان
   `factory/machines/{id}/sensors` بحمولة JSON. جرّبه بالمحاكي: `python -m erp.iot.simulator`.

## 🚀 التشغيل

```bash
# 1) تثبيت المتطلبات
pip install -r requirements.txt

# 2) (اختياري) تعبئة بيانات تجريبية: منتجات، آلات، 90 يوم مبيعات، أوامر إنتاج
python -m erp.seed

# 3) تشغيل الخادم
uvicorn erp.main:app --reload

# لوحة التحكم المرئية:        http://localhost:8000/
# الوثائق التفاعلية (Swagger): http://localhost:8000/docs
```

## 🔐 المصادقة والصلاحيات

- عمليات **القراءة** مفتوحة، وعمليات **الكتابة** (إضافة/تعديل/حذف) تتطلب تسجيل دخول بدور `admin` أو `manager`.
- بيانات seed تنشئ مستخدمًا افتراضيًا: `admin` / `admin123` — **غيّره في الإنتاج**، وعرّف مفتاح التوقيع عبر متغير البيئة `ERP_SECRET_KEY`.
- بدون seed: أول استدعاء لـ `POST /auth/register` ينشئ مدير النظام (Bootstrap).

```bash
# تسجيل الدخول والحصول على رمز
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# استخدام الرمز في عمليات الكتابة
curl -X POST http://localhost:8000/inventory/products \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"name": "منتج جديد", "sku": "NEW-1", "quantity": 100}'
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

# تقرير الرؤى والتوصيات المرتبة بالأولوية
curl http://localhost:8000/ai/insights
```

## 🧠 تفعيل مساعد Claude (اختياري)

```bash
export ANTHROPIC_API_KEY=sk-ant-...   # من https://platform.claude.com
# اختياريًا: export ERP_CLAUDE_MODEL=claude-opus-4-8
uvicorn erp.main:app --reload
# الآن POST /ai/assistant يجيب بنموذج Claude على الأسئلة الحرة والمعقدة
```

## 📡 تفعيل استقبال الحساسات عبر MQTT (اختياري)

```bash
export ERP_MQTT_BROKER=localhost      # عنوان وسيط MQTT (مثل mosquitto)
uvicorn erp.main:app &
python -m erp.iot.simulator 20        # نشر 20 قراءة تجريبية
```

## 🗂️ بنية المشروع

```
erp/
├── main.py            # تطبيق FastAPI وتجميع المسارات
├── database.py        # إعداد SQLite + SQLAlchemy
├── models.py          # جداول قاعدة البيانات
├── schemas.py         # مخططات Pydantic
├── auth.py            # المصادقة والصلاحيات (PBKDF2 + HMAC tokens)
├── seed.py            # بيانات تجريبية
├── static/
│   └── dashboard.html # لوحة التحكم المرئية (عربية RTL، بدون مكتبات خارجية)
├── ai/
│   ├── predictive_maintenance.py   # الصيانة التنبؤية (Random Forest)
│   ├── demand_forecast.py          # توقع الطلب (Linear Regression)
│   ├── anomaly_detection.py        # كشف شذوذ الجودة (Isolation Forest)
│   ├── assistant.py                # المساعد القاعدي بالعربية
│   ├── llm_assistant.py            # مساعد Claude للأسئلة الحرة (اختياري)
│   └── insights.py                 # تقرير الرؤى والتوصيات بالأولوية
├── iot/
│   ├── mqtt_ingest.py              # استقبال قراءات الحساسات عبر MQTT
│   └── simulator.py                # محاكي حساسات للتجربة
└── routers/
    ├── auth.py        # تسجيل الدخول وإدارة المستخدمين
    ├── dashboard.py   # لوحة التحكم + المساعد
    ├── inventory.py   # المخزون
    ├── machines.py    # الآلات والصيانة
    ├── production.py  # الإنتاج والجودة
    ├── sales.py       # المبيعات
    └── employees.py   # الموظفون
```

> ملاحظة: يحتوي المستودع أيضًا على `main.py` في الجذر وهو API قديم لتشخيص أعطال السيارات، مستقل عن نظام الـ ERP.

# أكواد Python لأجهزة MCU داخل Packet Tracer

هذه الأكواد بديل متقدّم عن «الشروط» الجاهزة في سيرفر إنترنت الأشياء،
وتعطي منطقًا أذكى يرفع تقييم المشروع.

| الملف | الوظيفة | المنافذ |
|---|---|---|
| [`smoke_siren_mcu.py`](smoke_siren_mcu.py) | دخان + سايرن مع تأكيد 3 ثوانٍ ضد الإنذار الكاذب | Smoke→A0 · Siren→D0 |
| [`motion_light_mcu.py`](motion_light_mcu.py) | حركة + إضاءة مع مؤقّت إطفاء 10 ثوانٍ | Motion→D0 · Lamp→D1 |
| [`fire_system_mcu.py`](fire_system_mcu.py) | نظام حريق بثلاثة مستويات خطر | Fire→D0 · Smoke→A0 · Siren→D1 · Sprinkler→D2 · Door→D3 |
| [`rfid_door_mcu.py`](rfid_door_mcu.py) | RFID مع قائمة بطاقات وقفل بعد 3 محاولات فاشلة | Reader→A0 · Door→D0 · Siren→D1 |

---

## كيف تشغّل الكود في Packet Tracer

1. اسحب جهاز **MCU** من `Components → Boards → MCU-PT` إلى مساحة العمل
2. وصّل الحساسات والمشغّلات بمنافذ الـ MCU باستخدام
   **IoT Custom Cable** (الكابل البنفسجي في قائمة الكابلات)
3. اضغط على الـ MCU ← تبويب **Programming**
4. اضغط **New** ← اختر القالب **`Empty - Python`** ← سمّ المشروع
5. افتح ملف `main.py` واحذف محتواه ← الصق الكود من هنا
6. اضغط **Run** ▶
7. راقب الرسائل في نافذة الـ Console أسفل المحرّر

---

## ملاحظات مهمة

| النقطة | التوضيح |
|---|---|
| **المنافذ** | تأكد أن رقم المنفذ في الكود يطابق المنفذ الذي وصّلت فيه الجهاز فعليًا |
| **العتبات** | قيم مثل `THRESHOLD = 0.5` تقريبية — راقب القراءة الحقيقية في جهازك واضبطها |
| **`analogRead`** | يرجع قيمة بين `0` و `1023` — لذلك نقسم على `1023.0` للحصول على نسبة |
| **`delay()`** | بالميلي ثانية، وهي دالة خاصة ببيئة Packet Tracer وليست Python العادية |
| **لا تشغّلها خارج Packet Tracer** | مكتبات `gpio` و `time` هنا خاصة ببيئة المحاكاة |

---

## دوال بيئة Packet Tracer المستخدمة

```python
from gpio import *
from time import *

pinMode(pin, IN|OUT)        # تحديد اتجاه المنفذ
digitalRead(pin)            # قراءة رقمية: HIGH أو LOW
digitalWrite(pin, HIGH|LOW) # كتابة رقمية
analogRead(pin)             # قراءة تناظرية: 0 - 1023
analogWrite(pin, value)     # كتابة تناظرية: 0 - 255
delay(ms)                   # تأخير بالميلي ثانية
```

**رجوع إلى:** [الفهرس الرئيسي](../README.md)

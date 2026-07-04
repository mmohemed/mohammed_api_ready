# =========================================
# بيانات تجريبية لتجربة النظام فورًا
# التشغيل: python -m erp.seed
# =========================================
import random
from datetime import datetime, timedelta

from .auth import hash_password
from .database import Base, SessionLocal, engine
from .models import Employee, Machine, Product, ProductionOrder, SalesOrder, SensorReading, User


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Product).count() > 0:
            print("قاعدة البيانات تحتوي على بيانات بالفعل — لن تتم الإضافة.")
            return

        random.seed(7)

        # ---------- مستخدم افتراضي ----------
        if db.query(User).count() == 0:
            db.add(User(username="admin", full_name="مدير النظام",
                        password_hash=hash_password("admin123"), role="admin"))

        # ---------- منتجات ----------
        products = [
            Product(name="أنبوب PVC 2 بوصة", sku="PVC-2IN", category="بلاستيك",
                    quantity=850, reorder_point=200, unit_cost=12, unit_price=20, unit="متر"),
            Product(name="صفيحة ألمنيوم 3مم", sku="ALU-3MM", category="معادن",
                    quantity=120, reorder_point=150, unit_cost=45, unit_price=70, unit="لوح"),
            Product(name="كابل نحاس 4مم", sku="CU-4MM", category="كهرباء",
                    quantity=3000, reorder_point=500, unit_cost=8, unit_price=14, unit="متر"),
            Product(name="خزان مياه 500 لتر", sku="TNK-500", category="بلاستيك",
                    quantity=40, reorder_point=15, unit_cost=300, unit_price=480),
        ]
        db.add_all(products)
        db.flush()

        # ---------- آلات ----------
        machines = [
            Machine(name="خط البثق رقم 1", machine_type="بثق بلاستيك"),
            Machine(name="مكبس هيدروليكي A", machine_type="تشكيل معادن"),
            Machine(name="آلة سحب الكابلات", machine_type="سحب نحاس"),
        ]
        db.add_all(machines)
        db.flush()

        # قراءات حساسات: الأولى طبيعية، الثانية مجهدة (لتجربة التنبؤ بالعطل)
        profiles = {
            machines[0].id: (65, 2.5, 5.0, 200),    # طبيعية
            machines[1].id: (98, 6.5, 6.8, 900),    # مجهدة -> خطر مرتفع
            machines[2].id: (75, 3.5, 5.2, 450),    # متوسطة
        }
        now = datetime.utcnow()
        for machine_id, (t, v, p, h) in profiles.items():
            for i in range(10):
                db.add(SensorReading(
                    machine_id=machine_id,
                    temperature=t + random.uniform(-3, 3),
                    vibration=max(0.1, v + random.uniform(-0.4, 0.4)),
                    pressure=max(1, p + random.uniform(-0.3, 0.3)),
                    running_hours=h + i * 8,
                    recorded_at=now - timedelta(hours=(10 - i) * 8),
                ))

        # ---------- مبيعات تاريخية (90 يومًا) للتنبؤ بالطلب ----------
        customers = ["شركة البناء الحديث", "مؤسسة الأنوار", "مصنع الخليج", "شركة الأمل التجارية"]
        for day in range(90, 0, -1):
            date = now - timedelta(days=day)
            for product in products:
                if random.random() < 0.6:
                    base = {"PVC-2IN": 40, "ALU-3MM": 8, "CU-4MM": 150, "TNK-500": 2}[product.sku]
                    growth = 1 + (90 - day) * 0.004  # طلب متزايد بمرور الوقت
                    qty = max(1, round(base * growth * random.uniform(0.5, 1.5)))
                    db.add(SalesOrder(
                        product_id=product.id,
                        customer_name=random.choice(customers),
                        quantity=qty,
                        unit_price=product.unit_price,
                        status="delivered",
                        ordered_at=date,
                    ))

        # ---------- أوامر إنتاج مكتملة (لكشف الشذوذ) ----------
        for i in range(12):
            planned = random.choice([500, 800, 1000])
            if i == 5:   # أمر شاذ: عيوب مرتفعة جدًا
                produced, defective = planned * 0.9, planned * 0.25
            elif i == 9:  # أمر شاذ: إنجاز منخفض جدًا
                produced, defective = planned * 0.45, planned * 0.02
            else:
                produced = planned * random.uniform(0.92, 1.0)
                defective = produced * random.uniform(0.005, 0.03)
            db.add(ProductionOrder(
                product_id=random.choice(products).id,
                machine_id=random.choice(machines).id,
                planned_quantity=planned,
                produced_quantity=round(produced),
                defective_quantity=round(defective),
                status="completed",
                created_at=now - timedelta(days=30 - i * 2),
                completed_at=now - timedelta(days=29 - i * 2),
            ))

        # ---------- موظفون ----------
        db.add_all([
            Employee(name="محمد أحمد", role="مدير إنتاج", department="الإنتاج", salary=9000),
            Employee(name="خالد سعيد", role="فني صيانة", department="الصيانة", salary=6000),
            Employee(name="سارة علي", role="مسؤولة جودة", department="الجودة", salary=6500),
            Employee(name="عمر حسن", role="عامل إنتاج", department="الإنتاج", salary=4000),
            Employee(name="فاطمة يوسف", role="محاسبة", department="المالية", salary=7000),
        ])

        db.commit()
        print("✅ تم إنشاء البيانات التجريبية بنجاح:")
        print(f"   - {len(products)} منتجات، {len(machines)} آلات مع قراءات حساسات")
        print("   - 90 يومًا من المبيعات، 12 أمر إنتاج، 5 موظفين")
        print("   - مستخدم افتراضي: admin / admin123 ⚠️ غيّر كلمة المرور في الإنتاج")
    finally:
        db.close()


if __name__ == "__main__":
    seed()

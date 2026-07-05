# =========================================
# الصيانة التنبؤية للآلات
# نموذج تصنيف يتوقع احتمال العطل من قراءات الحساسات
# يُدرَّب عند بدء التشغيل على بيانات فيزيائية اصطناعية
# =========================================
import numpy as np
from sklearn.ensemble import RandomForestClassifier

_model: RandomForestClassifier | None = None

# المدى الطبيعي لكل مؤشر: (متوسط طبيعي، انحراف)
FEATURES = ["temperature", "vibration", "pressure", "running_hours"]


def _generate_training_data(n: int = 4000, seed: int = 42):
    """توليد بيانات تدريب اصطناعية: الآلة تتعطل غالبًا عند حرارة/اهتزاز مرتفعين
    وساعات تشغيل طويلة منذ آخر صيانة."""
    rng = np.random.default_rng(seed)
    temperature = rng.normal(70, 15, n).clip(20, 130)      # مئوية
    vibration = rng.normal(3, 1.5, n).clip(0.1, 12)        # ملم/ثانية
    pressure = rng.normal(5, 1.2, n).clip(1, 10)           # بار
    running_hours = rng.uniform(0, 1200, n)                # ساعات منذ آخر صيانة

    # درجة إجهاد فيزيائية تقريبية
    stress = (
        0.035 * np.maximum(temperature - 80, 0)
        + 0.45 * np.maximum(vibration - 4.5, 0)
        + 0.25 * np.abs(pressure - 5)
        + 0.0022 * np.maximum(running_hours - 500, 0)
    )
    prob_fail = 1 / (1 + np.exp(-(stress - 1.2) * 2.2))
    y = (rng.uniform(0, 1, n) < prob_fail).astype(int)

    X = np.column_stack([temperature, vibration, pressure, running_hours])
    return X, y


def get_model() -> RandomForestClassifier:
    global _model
    if _model is None:
        X, y = _generate_training_data()
        _model = RandomForestClassifier(n_estimators=120, random_state=42)
        _model.fit(X, y)
    return _model


def predict_failure(temperature: float, vibration: float, pressure: float, running_hours: float) -> dict:
    """يعيد احتمال العطل وتوصية صيانة بالعربية."""
    model = get_model()
    X = np.array([[temperature, vibration, pressure, running_hours]])
    probability = float(model.predict_proba(X)[0][1])

    if probability >= 0.7:
        level, action = "خطر مرتفع", "أوقف الآلة وقم بصيانة فورية قبل حدوث عطل مكلف."
    elif probability >= 0.4:
        level, action = "خطر متوسط", "جدولة صيانة وقائية خلال الأيام القادمة ومراقبة القراءات."
    else:
        level, action = "خطر منخفض", "الآلة تعمل ضمن المدى الطبيعي، تابع المراقبة الدورية."

    # أهم العوامل المساهمة في القرار
    importances = dict(zip(FEATURES, model.feature_importances_.round(3).tolist()))

    return {
        "failure_probability": round(probability, 3),
        "risk_level": level,
        "recommendation": action,
        "feature_importance": importances,
    }

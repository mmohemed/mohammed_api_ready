# =========================================
# كشف الشذوذ في جودة الإنتاج
# Isolation Forest على نسب العيوب ومعدلات الإنجاز
# =========================================
import numpy as np
from sklearn.ensemble import IsolationForest


def detect_production_anomalies(orders: list[dict]) -> dict:
    """يستقبل أوامر إنتاج مكتملة (planned, produced, defective) ويحدد الأوامر الشاذة.

    كل أمر dict فيه: id, planned_quantity, produced_quantity, defective_quantity."""
    completed = [o for o in orders if o["produced_quantity"] > 0]
    if len(completed) < 5:
        return {
            "status": "no_data",
            "message": "نحتاج 5 أوامر إنتاج مكتملة على الأقل لكشف الشذوذ.",
            "anomalies": [],
        }

    features = []
    for o in completed:
        defect_rate = o["defective_quantity"] / o["produced_quantity"]
        completion_rate = o["produced_quantity"] / max(o["planned_quantity"], 1e-9)
        features.append([defect_rate, completion_rate])

    X = np.array(features)
    model = IsolationForest(contamination=0.15, random_state=42)
    labels = model.fit_predict(X)

    anomalies = []
    for order, label, (defect_rate, completion_rate) in zip(completed, labels, features):
        if label == -1:
            reasons = []
            if defect_rate > np.median(X[:, 0]):
                reasons.append(f"نسبة عيوب مرتفعة ({defect_rate:.1%})")
            if completion_rate < np.median(X[:, 1]):
                reasons.append(f"نسبة إنجاز منخفضة ({completion_rate:.1%})")
            anomalies.append({
                "order_id": order["id"],
                "defect_rate": round(defect_rate, 3),
                "completion_rate": round(completion_rate, 3),
                "reasons": reasons or ["نمط غير معتاد مقارنة ببقية الأوامر"],
            })

    return {
        "status": "ok",
        "orders_analyzed": len(completed),
        "anomalies_found": len(anomalies),
        "anomalies": anomalies,
        "message": (
            f"⚠️ تم رصد {len(anomalies)} أمر إنتاج بسلوك غير طبيعي — راجع خط الإنتاج والجودة."
            if anomalies else "✅ لا يوجد شذوذ ملحوظ في جودة الإنتاج."
        ),
    }

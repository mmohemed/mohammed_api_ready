# =========================================
# API لتشخيص أعطال السيارات
# يدعم اللغة العربية
# =========================================

from fastapi import FastAPI
from pydantic import BaseModel
import joblib
import os

# -----------------------------
# 1️⃣ إنشاء التطبيق
# -----------------------------
app = FastAPI(
    title="Car Problems AI API",
    description="API لتشخيص أعطال السيارات مع اللغة العربية",
    version="1.0"
)

# -----------------------------
# 2️⃣ تحميل النماذج والـVectorizer
# -----------------------------
base_path = os.path.dirname(os.path.abspath(__file__))

model_problem = joblib.load(os.path.join(base_path, "model_problem.pkl"))
model_risk    = joblib.load(os.path.join(base_path, "model_risk.pkl"))
model_solution= joblib.load(os.path.join(base_path, "model_solution.pkl"))
vectorizer    = joblib.load(os.path.join(base_path, "vectorizer.pkl"))

# -----------------------------
# 3️⃣ تعريف نموذج البيانات للـPOST
# -----------------------------
class CarProblemRequest(BaseModel):
    text: str

# -----------------------------
# 4️⃣ دالة التنبؤ
# -----------------------------
def predict_car_problem(text: str):
    vec = vectorizer.transform([text])
    problem  = model_problem.predict(vec)[0]
    risk     = model_risk.predict(vec)[0]
    solution = model_solution.predict(vec)[0]
    return {"problem": problem, "risk": risk, "solution": solution}

# -----------------------------
# 5️⃣ المسار الأساسي
# -----------------------------
@app.get("/")
def root():
    return {"message": "مرحبًا بك في API تشخيص أعطال السيارات!"}

# -----------------------------
# 6️⃣ مسار التنبؤ
# -----------------------------
@app.post("/predict")
def predict(request: CarProblemRequest):
    result = predict_car_problem(request.text)
    return result

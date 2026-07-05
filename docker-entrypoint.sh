#!/bin/sh
set -e

mkdir -p /app/data

# بيانات تجريبية عند أول تشغيل — السكربت لا يكرر البيانات إن وُجدت
# (تخطَّ التعبئة نهائيًا بتعريف ERP_SKIP_SEED=1)
if [ -z "$ERP_SKIP_SEED" ]; then
    python -m erp.seed
fi

exec uvicorn erp.main:app --host 0.0.0.0 --port 8000

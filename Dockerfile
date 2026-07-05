# Smart Factory ERP 🏭
# البناء:   docker build -t smart-erp .
# التشغيل:  docker run -p 8000:8000 smart-erp
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY erp/ ./erp/

# تعبئة البيانات التجريبية عند أول تشغيل فقط (إن لم توجد قاعدة بيانات)
COPY docker-entrypoint.sh .
RUN chmod +x docker-entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["./docker-entrypoint.sh"]

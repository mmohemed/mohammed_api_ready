# =========================================
# استقبال قراءات الحساسات من أجهزة المصنع عبر MQTT
#
# التفعيل: عرّف متغير البيئة ERP_MQTT_BROKER (مثال: localhost أو 192.168.1.10)
#          واختياريًا ERP_MQTT_PORT (افتراضي 1883)
# بدون المتغير لا يتم الاتصال بأي وسيط ويبقى الإدخال اليدوي عبر الـ API.
#
# صيغة الرسائل:
#   Topic:   factory/machines/{machine_id}/sensors
#   Payload: {"temperature": 72.5, "vibration": 3.1, "pressure": 5.0, "running_hours": 320}
# =========================================
import json
import logging
import os
import threading

from ..database import SessionLocal
from ..models import Machine, SensorReading

logger = logging.getLogger("erp.iot")

TOPIC_PATTERN = "factory/machines/+/sensors"
REQUIRED_FIELDS = ("temperature", "vibration", "pressure", "running_hours")


def parse_topic_machine_id(topic: str) -> int | None:
    """يستخرج رقم الآلة من العنوان factory/machines/{id}/sensors"""
    parts = topic.split("/")
    if len(parts) == 4 and parts[0] == "factory" and parts[1] == "machines" and parts[3] == "sensors":
        try:
            return int(parts[2])
        except ValueError:
            return None
    return None


def ingest_reading(topic: str, payload: bytes | str) -> dict:
    """يعالج رسالة MQTT واحدة ويخزنها كقراءة حساسات.

    دالة مستقلة عن الاتصال نفسه ليمكن اختبارها بدون وسيط MQTT."""
    machine_id = parse_topic_machine_id(topic)
    if machine_id is None:
        return {"status": "error", "reason": f"عنوان غير صالح: {topic}"}

    try:
        data = json.loads(payload)
        values = {field: float(data[field]) for field in REQUIRED_FIELDS}
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        return {"status": "error", "reason": f"حمولة غير صالحة: {exc}"}

    db = SessionLocal()
    try:
        if not db.get(Machine, machine_id):
            return {"status": "error", "reason": f"لا توجد آلة برقم {machine_id}"}
        db.add(SensorReading(machine_id=machine_id, **values))
        db.commit()
        return {"status": "ok", "machine_id": machine_id, **values}
    finally:
        db.close()


def start_mqtt_listener() -> bool:
    """يشغّل مستمع MQTT في خيط خلفي إن كان ERP_MQTT_BROKER معرّفًا.

    يعيد True إذا بدأ الاستماع فعلًا."""
    broker = os.environ.get("ERP_MQTT_BROKER")
    if not broker:
        return False

    try:
        import paho.mqtt.client as mqtt
    except ImportError:
        logger.warning("ERP_MQTT_BROKER معرّف لكن مكتبة paho-mqtt غير مثبتة: pip install paho-mqtt")
        return False

    port = int(os.environ.get("ERP_MQTT_PORT", "1883"))

    def on_connect(client, userdata, flags, reason_code, properties=None):
        client.subscribe(TOPIC_PATTERN)
        logger.info("متصل بوسيط MQTT %s:%s ومشترك في %s", broker, port, TOPIC_PATTERN)

    def on_message(client, userdata, msg):
        result = ingest_reading(msg.topic, msg.payload)
        if result["status"] == "ok":
            logger.info("قراءة جديدة من الآلة %s", result["machine_id"])
        else:
            logger.warning("رسالة مرفوضة: %s", result["reason"])

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message

    def run():
        try:
            client.connect(broker, port, keepalive=60)
            client.loop_forever(retry_first_connection=True)
        except Exception as exc:
            logger.error("فشل الاتصال بوسيط MQTT %s:%s — %s", broker, port, exc)

    threading.Thread(target=run, daemon=True, name="erp-mqtt-listener").start()
    return True

# =========================================
# محاكي حساسات: ينشر قراءات وهمية عبر MQTT لتجربة النظام
# التشغيل: python -m erp.iot.simulator [عدد الرسائل]
# يتطلب: pip install paho-mqtt + وسيط MQTT (مثل mosquitto) على ERP_MQTT_BROKER
# =========================================
import json
import os
import random
import sys
import time


def main(messages_count: int = 20):
    import paho.mqtt.client as mqtt

    broker = os.environ.get("ERP_MQTT_BROKER", "localhost")
    port = int(os.environ.get("ERP_MQTT_PORT", "1883"))

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(broker, port)
    client.loop_start()

    machine_ids = [1, 2, 3]
    print(f"نشر {messages_count} قراءة إلى {broker}:{port} ...")
    for i in range(messages_count):
        machine_id = random.choice(machine_ids)
        payload = {
            "temperature": round(random.uniform(55, 105), 1),
            "vibration": round(random.uniform(1, 8), 2),
            "pressure": round(random.uniform(3.5, 7.5), 2),
            "running_hours": round(random.uniform(50, 1000), 0),
        }
        topic = f"factory/machines/{machine_id}/sensors"
        client.publish(topic, json.dumps(payload), qos=1)
        print(f"  [{i + 1}] {topic} -> {payload}")
        time.sleep(0.5)

    client.loop_stop()
    client.disconnect()
    print("✅ انتهى النشر.")


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    main(count)

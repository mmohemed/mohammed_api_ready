# ==========================================================
#  نظام الحريق المتكامل - Packet Tracer MCU (Python)
# ==========================================================
#  التوصيل : Fire Monitor    -> D0   (مدخل رقمي)
#            Smoke Detector  -> A0   (مدخل تناظري)
#            Siren           -> D1   (مخرج)
#            Fire Sprinkler  -> D2   (مخرج)
#            Door Lock       -> D3   (مخرج - LOW = مفتوح للإخلاء)
#
#  المنطق  : ثلاثة مستويات إنذار
#            المستوى 1 : دخان فقط        -> سايرن
#            المستوى 2 : دخان كثيف       -> سايرن + فتح الباب
#            المستوى 3 : نار مؤكدة       -> سايرن + مرشّات + فتح الباب
# ==========================================================

from gpio import *
from time import *

FIRE_PIN      = D0
SMOKE_PIN     = A0
SIREN_PIN     = D1
SPRINKLER_PIN = D2
DOOR_PIN      = D3

SMOKE_WARN   = 0.35     # عتبة التحذير
SMOKE_DANGER = 0.70     # عتبة الخطر
SAMPLE_MS    = 300

LEVEL_NAMES = {0: "NORMAL", 1: "WARNING", 2: "DANGER", 3: "FIRE"}


def read_smoke():
    return analogRead(SMOKE_PIN) / 1023.0


def apply_level(level):
    """تطبيق المخرجات حسب مستوى الخطر"""
    siren     = level >= 1
    door_open = level >= 2      # الباب يُفتح للإخلاء
    sprinkler = level >= 3

    digitalWrite(SIREN_PIN,     HIGH if siren else LOW)
    digitalWrite(SPRINKLER_PIN, HIGH if sprinkler else LOW)
    # LOW على منفذ الباب = إلغاء القفل (إخلاء)
    digitalWrite(DOOR_PIN,      LOW if door_open else HIGH)


def main():
    pinMode(FIRE_PIN, IN)
    pinMode(SMOKE_PIN, IN)
    pinMode(SIREN_PIN, OUT)
    pinMode(SPRINKLER_PIN, OUT)
    pinMode(DOOR_PIN, OUT)

    last_level = -1
    print("Fire safety system started...")

    while True:
        fire  = digitalRead(FIRE_PIN) == HIGH
        smoke = read_smoke()

        if fire:
            level = 3
        elif smoke >= SMOKE_DANGER:
            level = 2
        elif smoke >= SMOKE_WARN:
            level = 1
        else:
            level = 0

        if level != last_level:
            apply_level(level)
            print("Level -> %s  (smoke=%.2f, fire=%s)"
                  % (LEVEL_NAMES[level], smoke, fire))
            last_level = level

        delay(SAMPLE_MS)


if __name__ == "__main__":
    main()

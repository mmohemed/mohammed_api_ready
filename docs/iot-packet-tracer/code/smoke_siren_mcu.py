# ==========================================================
#  نظام إنذار الدخان - Packet Tracer MCU (Python)
# ==========================================================
#  الجهاز   : MCU-PT
#  التوصيل  : Smoke Detector  ->  A0   (مدخل تناظري)
#             Siren           ->  D0   (مخرج رقمي)
#  الميزة   : لا يُطلق الإنذار إلا إذا استمر الدخان 3 ثوانٍ
#             وهذا يمنع الإنذارات الكاذبة (بخار مطبخ، دخان سيجارة)
# ==========================================================

from gpio import *
from time import *

SMOKE_PIN = A0          # منفذ مستشعر الدخان
SIREN_PIN = D0          # منفذ صفارة الإنذار

THRESHOLD    = 0.5      # عتبة الدخان (اضبطها حسب القراءة الفعلية عندك)
CONFIRM_MS   = 3000     # مدة التأكيد قبل الإنذار (3 ثوانٍ)
SAMPLE_MS    = 250      # زمن أخذ العينة

CONFIRM_LOOPS = CONFIRM_MS // SAMPLE_MS


def read_smoke():
    """قراءة مستوى الدخان وتحويلها إلى نسبة من 0 إلى 1"""
    raw = analogRead(SMOKE_PIN)
    return raw / 1023.0


def siren(on):
    digitalWrite(SIREN_PIN, HIGH if on else LOW)


def main():
    pinMode(SMOKE_PIN, IN)
    pinMode(SIREN_PIN, OUT)
    siren(False)

    over_threshold = 0       # عدّاد العينات التي تجاوزت العتبة
    alarming = False

    print("Smoke alarm system started...")

    while True:
        level = read_smoke()

        if level > THRESHOLD:
            over_threshold += 1
        else:
            over_threshold = 0
            if alarming:
                alarming = False
                siren(False)
                print("Smoke cleared - siren OFF")

        # الإنذار فقط بعد التأكيد المستمر
        if over_threshold >= CONFIRM_LOOPS and not alarming:
            alarming = True
            siren(True)
            print("SMOKE CONFIRMED (level=%.2f) - SIREN ON" % level)

        delay(SAMPLE_MS)


if __name__ == "__main__":
    main()

# ==========================================================
#  إضاءة ذكية بمستشعر الحركة - Packet Tracer MCU (Python)
# ==========================================================
#  التوصيل : Motion Detector -> D0  (مدخل رقمي)
#            Lamp            -> D1  (مخرج رقمي)
#  الميزة  : المصباح يبقى مضاءً 10 ثوانٍ بعد آخر حركة،
#            فلا ينطفئ في وجه المستخدم إذا توقّف لحظة.
# ==========================================================

from gpio import *
from time import *

MOTION_PIN = D0
LAMP_PIN   = D1

HOLD_MS   = 10000       # مدة بقاء الإضاءة بعد آخر حركة
SAMPLE_MS = 200

HOLD_LOOPS = HOLD_MS // SAMPLE_MS


def main():
    pinMode(MOTION_PIN, IN)
    pinMode(LAMP_PIN, OUT)
    digitalWrite(LAMP_PIN, LOW)

    idle_loops = 0
    lamp_on = False

    print("Motion light system started...")

    while True:
        motion = digitalRead(MOTION_PIN)

        if motion == HIGH:
            idle_loops = 0
            if not lamp_on:
                lamp_on = True
                digitalWrite(LAMP_PIN, HIGH)
                print("Motion detected - LAMP ON")
        else:
            idle_loops += 1
            if lamp_on and idle_loops >= HOLD_LOOPS:
                lamp_on = False
                digitalWrite(LAMP_PIN, LOW)
                print("No motion for 10s - LAMP OFF")

        delay(SAMPLE_MS)


if __name__ == "__main__":
    main()

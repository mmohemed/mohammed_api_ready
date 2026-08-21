# ==========================================================
#  التحكم بالباب عبر RFID - Packet Tracer MCU (Python)
# ==========================================================
#  التوصيل : RFID Reader -> A0  (يعطي رقم البطاقة)
#            Door Lock   -> D0  (HIGH = مقفل)
#            Siren       -> D1
#
#  الميزة  : قائمة بطاقات مصرَّح بها + قفل مؤقّت بعد 3 محاولات فاشلة
#  ملاحظة  : استبدل الأرقام في AUTHORIZED بأرقام بطاقاتك الفعلية
#            (Config -> Settings -> Card ID على كل بطاقة)
# ==========================================================

from gpio import *
from time import *

READER_PIN = A0
DOOR_PIN   = D0
SIREN_PIN  = D1

AUTHORIZED = {
    1001: "Mohammed (Manager)",
    1002: "Ahmed (Staff)",
    1003: "Sara (Security)",
}

MAX_FAILS    = 3
LOCKOUT_MS   = 15000     # قفل 15 ثانية بعد 3 محاولات فاشلة
OPEN_MS      = 5000      # يبقى الباب مفتوحًا 5 ثوانٍ
SAMPLE_MS    = 300


def lock_door(locked):
    digitalWrite(DOOR_PIN, HIGH if locked else LOW)


def siren(on):
    digitalWrite(SIREN_PIN, HIGH if on else LOW)


def main():
    pinMode(READER_PIN, IN)
    pinMode(DOOR_PIN, OUT)
    pinMode(SIREN_PIN, OUT)

    lock_door(True)
    siren(False)

    fails = 0
    last_card = 0

    print("RFID access control started...")

    while True:
        card = int(analogRead(READER_PIN))

        # نتعامل فقط مع بطاقة جديدة (لا نكرّر نفس القراءة)
        if card != 0 and card != last_card:
            last_card = card

            if card in AUTHORIZED:
                print("ACCESS GRANTED -> %s (id=%d)" % (AUTHORIZED[card], card))
                fails = 0
                siren(False)
                lock_door(False)
                delay(OPEN_MS)
                lock_door(True)
                print("Door re-locked")
            else:
                fails += 1
                print("ACCESS DENIED (id=%d) - attempt %d/%d"
                      % (card, fails, MAX_FAILS))
                siren(True)
                delay(1500)
                siren(False)

                if fails >= MAX_FAILS:
                    print("TOO MANY FAILURES - LOCKOUT for 15s")
                    siren(True)
                    delay(LOCKOUT_MS)
                    siren(False)
                    fails = 0

        elif card == 0:
            last_card = 0

        delay(SAMPLE_MS)


if __name__ == "__main__":
    main()

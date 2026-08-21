# 03 — الراوترات والربط بين المدن (WAN)

الهدف: تشغيل التوجيه بين الـ VLANs داخل كل مدينة (Router-on-a-Stick)،
ثم ربط **صنعاء ↔ عدن** عبر خطوط Serial وبروتوكول **OSPF**.

---

## 1) تجهيز المنافذ Serial أولًا ⚠️

الراوتر 2911 لا يحتوي منافذ Serial افتراضيًا. لكل راوتر:

1. اضغط على الراوتر ← تبويب **Physical**
2. **أطفئ الراوتر** من زر الطاقة (المفتاح الأخضر على الصورة)
3. اسحب الوحدة **`HWIC-2T`** من القائمة اليسرى إلى إحدى الفتحات الفارغة
4. **شغّل الراوتر** مرة أخرى
5. ستظهر لك المنافذ `Serial0/0/0` و `Serial0/0/1`

> نسيان إطفاء الراوتر قبل تركيب الوحدة = رسالة خطأ ولن تُركَّب الوحدة.

**توصيل الكابل:** استخدم **Serial DCE**، وابدأ السحب من الراوتر الذي
ستكتب فيه `clock rate` (الطرف الذي يظهر عليه رمز الساعة ⏱).

---

## 2) الراوتر R1-SANAA

```cisco
enable
configure terminal
!
hostname R1-SANAA
no ip domain-lookup
ip domain-name smartcity.local
!
! ===== المنفذ الفيزيائي نحو السويتش =====
interface GigabitEthernet0/0
 no ip address
 no shutdown
 exit
!
! ===== Router-on-a-Stick : منفذ فرعي لكل VLAN =====
interface GigabitEthernet0/0.10
 description VLAN 10 - SERVERS
 encapsulation dot1Q 10
 ip address 192.168.10.1 255.255.255.0
 exit
!
interface GigabitEthernet0/0.20
 description VLAN 20 - USERS
 encapsulation dot1Q 20
 ip address 192.168.20.1 255.255.255.0
 ip helper-address 192.168.10.10
 exit
!
interface GigabitEthernet0/0.30
 description VLAN 30 - IOT
 encapsulation dot1Q 30
 ip address 192.168.30.1 255.255.255.0
 ip helper-address 192.168.10.10
 exit
!
interface GigabitEthernet0/0.99
 description VLAN 99 - MGMT (Native)
 encapsulation dot1Q 99 native
 ip address 192.168.99.1 255.255.255.0
 exit
!
! ===== رابط الـ WAN نحو المزوّد =====
interface Serial0/0/0
 description WAN to R-ISP
 ip address 10.0.0.1 255.255.255.252
 clock rate 64000
 bandwidth 64
 no shutdown
 exit
!
! ===== التوجيه الديناميكي =====
router ospf 1
 router-id 1.1.1.1
 network 192.168.10.0 0.0.0.255 area 0
 network 192.168.20.0 0.0.0.255 area 0
 network 192.168.30.0 0.0.0.255 area 0
 network 192.168.99.0 0.0.0.255 area 0
 network 10.0.0.0 0.0.0.3 area 0
 passive-interface GigabitEthernet0/0.10
 passive-interface GigabitEthernet0/0.20
 passive-interface GigabitEthernet0/0.30
 exit
!
! ===== الأمان الأساسي =====
enable secret Cisco@123
username admin secret Admin@123
service password-encryption
!
line console 0
 login local
 logging synchronous
 exec-timeout 10 0
 exit
!
banner motd #  ****  R1-SANAA : Authorized Access Only  ****  #
!
end
write memory
```

### تفعيل SSH على R1

```cisco
configure terminal
ip domain-name smartcity.local
crypto key generate rsa
```
عندما يسألك عن حجم المفتاح اكتب: **`1024`**

```cisco
ip ssh version 2
line vty 0 4
 transport input ssh
 login local
 exec-timeout 10 0
 exit
end
write memory
```

> **ملاحظة:** سنعدّل `login local` لاحقًا إلى مصادقة RADIUS في
> [ملف 05](05-wireless-wpa2-aaa.md) عند إعداد AAA.

---

## 3) الراوتر R-ISP (راوتر المزوّد بين المدينتين)

```cisco
enable
configure terminal
!
hostname R-ISP
no ip domain-lookup
!
interface Serial0/0/0
 description Link to R1-SANAA
 ip address 10.0.0.2 255.255.255.252
 bandwidth 64
 no shutdown
 exit
!
interface Serial0/0/1
 description Link to R2-ADEN
 ip address 10.0.0.5 255.255.255.252
 clock rate 64000
 bandwidth 64
 no shutdown
 exit
!
! عنوان وهمي يمثّل "الإنترنت" لاختبار الوصول الخارجي
interface Loopback0
 ip address 8.8.8.8 255.255.255.255
 exit
!
router ospf 1
 router-id 2.2.2.2
 network 10.0.0.0 0.0.0.3 area 0
 network 10.0.0.4 0.0.0.3 area 0
 network 8.8.8.8 0.0.0.0 area 0
 exit
!
enable secret Cisco@123
end
write memory
```

---

## 4) الراوتر R2-ADEN

```cisco
enable
configure terminal
!
hostname R2-ADEN
no ip domain-lookup
ip domain-name smartcity.local
!
interface GigabitEthernet0/0
 no ip address
 no shutdown
 exit
!
interface GigabitEthernet0/0.20
 description VLAN 20 - USERS
 encapsulation dot1Q 20
 ip address 172.16.20.1 255.255.255.0
 exit
!
interface GigabitEthernet0/0.30
 description VLAN 30 - IOT
 encapsulation dot1Q 30
 ip address 172.16.30.1 255.255.255.0
 exit
!
interface GigabitEthernet0/0.40
 description VLAN 40 - CELL TOWER
 encapsulation dot1Q 40
 ip address 172.16.40.1 255.255.255.0
 exit
!
interface GigabitEthernet0/0.99
 description VLAN 99 - MGMT (Native)
 encapsulation dot1Q 99 native
 ip address 172.16.99.1 255.255.255.0
 exit
!
interface Serial0/0/0
 description WAN to R-ISP
 ip address 10.0.0.6 255.255.255.252
 bandwidth 64
 no shutdown
 exit
!
router ospf 1
 router-id 3.3.3.3
 network 172.16.20.0 0.0.0.255 area 0
 network 172.16.30.0 0.0.0.255 area 0
 network 172.16.40.0 0.0.0.255 area 0
 network 172.16.99.0 0.0.0.255 area 0
 network 10.0.0.4 0.0.0.3 area 0
 passive-interface GigabitEthernet0/0.20
 passive-interface GigabitEthernet0/0.30
 passive-interface GigabitEthernet0/0.40
 exit
!
enable secret Cisco@123
username admin secret Admin@123
service password-encryption
!
line console 0
 login local
 logging synchronous
 exit
!
end
write memory
```

> إعداد **DHCP على R2** موجود في [ملف 04](04-dhcp-dns.md).

---

## 5) لماذا OSPF وليس Static؟

| | Static Routing | **OSPF** |
|---|---|---|
| عدد الأوامر | يزيد مع كل شبكة جديدة | إعداد واحد يغطي الكل |
| عند تعطّل رابط | لا يتغيّر شيء ← انقطاع | يحسب مسارًا بديلًا تلقائيًا |
| التوسّع لمدينة ثالثة | تعديل يدوي في كل راوتر | تُضاف تلقائيًا |
| مناسب للمشروع | ❌ | ✅ |

إن أراد أستاذك **Static Routing** بدلًا منه، هذه البدائل:

```cisco
! على R1
ip route 172.16.0.0 255.255.0.0 10.0.0.2
ip route 0.0.0.0 0.0.0.0 10.0.0.2

! على R2
ip route 192.168.0.0 255.255.0.0 10.0.0.5
ip route 0.0.0.0 0.0.0.0 10.0.0.5

! على R-ISP
ip route 192.168.0.0 255.255.0.0 10.0.0.1
ip route 172.16.0.0 255.255.0.0 10.0.0.6
```

---

## 6) التحقق من الربط بين المدن

```cisco
show ip interface brief
show ip route
show ip ospf neighbor
show ip protocols
show controllers Serial0/0/0     ! لمعرفة أي طرف هو DCE
```

**`show ip ospf neighbor` على R-ISP يجب أن يُظهر جارَين:**

```
Neighbor ID  Pri  State     Dead Time  Address    Interface
1.1.1.1        0  FULL/  -  00:00:35   10.0.0.1   Serial0/0/0
3.3.3.3        0  FULL/  -  00:00:33   10.0.0.5   Serial0/0/1
```

**اختبارات الـ ping المطلوبة:**

```
R1# ping 10.0.0.2          ← الرابط المباشر
R1# ping 10.0.0.6          ← الطرف الآخر من WAN
R1# ping 172.16.20.1       ← داخل شبكة عدن
PC-صنعاء > ping 172.16.30.50   ← من مدينة إلى مدينة (الاختبار الحاسم)
```

---

## 7) أخطاء شائعة في الـ WAN

| المشكلة | السبب | الحل |
|---|---|---|
| المنفذ Serial حالته `down/down` | لم تُكتب `clock rate` على طرف الـ DCE | `show controllers Se0/0/0` لمعرفة الـ DCE ثم أضف `clock rate 64000` |
| `up/down` (Protocol down) | الطرف الآخر مطفأ أو عنوان في subnet مختلف | تأكد أن الطرفين في نفس الـ /30 و `no shutdown` |
| OSPF لا يكوّن جيران | خطأ في الـ `network` أو الـ wildcard mask | راجع الـ wildcard: /30 ← `0.0.0.3` و /24 ← `0.0.0.255` |
| ping ينجح بين الراوترات لكن ليس بين الأجهزة | الأجهزة ما لها Default Gateway | تحقّق من الـ Gateway في IP Configuration |

---

**التالي:** [04 — DHCP و DNS](04-dhcp-dns.md)

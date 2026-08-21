# 02 — الربط السلكي: السويتشات والـ VLANs

الهدف: بناء الشبكة السلكية، فصل الأقسام بـ VLANs، تجهيز الـ Trunk للراوتر،
وتفعيل حماية المنافذ.

---

## 1) توزيع منافذ السويتش SW1 (صنعاء)

| المنافذ | VLAN | الأجهزة الموصولة |
|---|---|---|
| `Fa0/1 – Fa0/5` | 10 – SERVERS | SRV-CORE، SRV-IOT، SRV-AAA، SRV-WEB |
| `Fa0/6 – Fa0/15` | 20 – USERS | أجهزة PC والطابعات |
| `Fa0/16 – Fa0/20` | 30 – IOT | AP-STAFF، HOME-GW (منفذ Internet) |
| `Fa0/21 – Fa0/24` | 99 – MGMT | منافذ احتياطية / إدارة |
| `Gi0/1` | Trunk | ↔ الراوتر R1-SANAA (منفذ Gi0/0) |

> **نوع الكابل:** كل ما سبق **Copper Straight-Through** (النحاسي المستقيم)،
> لأن الأجهزة مختلفة النوع (PC↔Switch، Router↔Switch).

---

## 2) إعداد السويتش SW1-SANAA

افتح السويتش ← تبويب **CLI** ← والصق:

```cisco
enable
configure terminal
!
hostname SW1-SANAA
no ip domain-lookup
!
! ===== إنشاء الـ VLANs =====
vlan 10
 name SERVERS
 exit
vlan 20
 name USERS
 exit
vlan 30
 name IOT
 exit
vlan 99
 name MGMT
 exit
!
! ===== منافذ السيرفرات =====
interface range FastEthernet0/1-5
 switchport mode access
 switchport access vlan 10
 spanning-tree portfast
 no shutdown
 exit
!
! ===== منافذ المستخدمين + حماية المنافذ =====
interface range FastEthernet0/6-15
 switchport mode access
 switchport access vlan 20
 switchport port-security
 switchport port-security maximum 2
 switchport port-security mac-address sticky
 switchport port-security violation restrict
 spanning-tree portfast
 no shutdown
 exit
!
! ===== منافذ أجهزة IoT واللاسلكي =====
interface range FastEthernet0/16-20
 switchport mode access
 switchport access vlan 30
 spanning-tree portfast
 no shutdown
 exit
!
! ===== إطفاء المنافذ غير المستخدمة (ممارسة أمنية) =====
interface range FastEthernet0/21-24
 switchport mode access
 switchport access vlan 99
 shutdown
 exit
!
! ===== منفذ الـ Trunk نحو الراوتر =====
interface GigabitEthernet0/1
 switchport mode trunk
 switchport trunk native vlan 99
 switchport trunk allowed vlan 10,20,30,99
 no shutdown
 exit
!
! ===== عنوان الإدارة =====
interface Vlan99
 ip address 192.168.99.2 255.255.255.0
 no shutdown
 exit
ip default-gateway 192.168.99.1
!
! ===== كلمات المرور =====
enable secret Cisco@123
username admin secret Admin@123
!
line console 0
 login local
 logging synchronous
 exec-timeout 10 0
 exit
!
banner motd #  ****  SmartCity SANAA - Authorized Access Only  ****  #
!
end
write memory
```

---

## 3) إعداد السويتش SW2-ADEN

```cisco
enable
configure terminal
!
hostname SW2-ADEN
no ip domain-lookup
!
vlan 20
 name USERS
 exit
vlan 30
 name IOT
 exit
vlan 40
 name CELL
 exit
vlan 99
 name MGMT
 exit
!
interface range FastEthernet0/1-10
 switchport mode access
 switchport access vlan 20
 spanning-tree portfast
 exit
!
interface range FastEthernet0/11-18
 switchport mode access
 switchport access vlan 30
 spanning-tree portfast
 exit
!
! منفذ الـ Central Office Server الخاص ببرج الاتصالات
interface range FastEthernet0/19-22
 switchport mode access
 switchport access vlan 40
 spanning-tree portfast
 exit
!
interface range FastEthernet0/23-24
 shutdown
 exit
!
interface GigabitEthernet0/1
 switchport mode trunk
 switchport trunk native vlan 99
 switchport trunk allowed vlan 20,30,40,99
 exit
!
interface Vlan99
 ip address 172.16.99.2 255.255.255.0
 no shutdown
 exit
ip default-gateway 172.16.99.1
!
enable secret Cisco@123
username admin secret Admin@123
line console 0
 login local
 logging synchronous
 exit
!
end
write memory
```

---

## 4) لماذا استخدمنا VLANs؟ (اكتبها في تقرير المشروع)

| السبب | الشرح |
|---|---|
| **الأمان** | أجهزة الـ IoT في VLAN منفصلة، فلو اختُرق حساس لا يصل إلى السيرفرات مباشرة |
| **تقليل البث** | كل VLAN نطاق بث (Broadcast Domain) مستقل ← أداء أفضل |
| **التنظيم** | كل قسم له شبكة واضحة وسهل تتبّع أي جهاز |
| **المرونة** | نقل موظف من قسم لآخر = تغيير VLAN المنفذ فقط، بدون تمديد كابلات |

---

## 5) التحقق من الإعداد

```cisco
show vlan brief
show interfaces trunk
show port-security
show port-security interface FastEthernet0/6
show interfaces status
show mac address-table
```

**النتيجة المتوقعة من `show vlan brief`:**

```
VLAN Name       Status    Ports
---- ---------- --------- -------------------------------
10   SERVERS    active    Fa0/1, Fa0/2, Fa0/3, Fa0/4, Fa0/5
20   USERS      active    Fa0/6 ... Fa0/15
30   IOT        active    Fa0/16 ... Fa0/20
99   MGMT       active    Fa0/21 ... Fa0/24
```

**النتيجة المتوقعة من `show interfaces trunk`:**

```
Port     Mode    Encapsulation  Status    Native vlan
Gi0/1    on      802.1q         trunking  99
Vlans allowed and active in management domain: 10,20,30,99
```

---

## 6) أخطاء شائعة وحلولها

| المشكلة | السبب | الحل |
|---|---|---|
| الأجهزة في نفس الـ VLAN لا تتبادل ping | المنفذ ما زال VLAN 1 | `show vlan brief` وتأكد أن المنفذ تحت الـ VLAN الصحيح |
| الـ Trunk لا يعمل | Native VLAN مختلف بين الطرفين | اجعل الـ Native VLAN = 99 على الراوتر والسويتش |
| ضوء المنفذ برتقالي دائمًا | نوع كابل خطأ أو المنفذ `shutdown` | غيّر الكابل إلى Straight-Through واكتب `no shutdown` |
| المنفذ يُغلق تلقائيًا (err-disabled) | Port-Security اكتشف MAC زائد | `shutdown` ثم `no shutdown` على المنفذ |

---

**التالي:** [03 — الراوترات والربط بين المدن](03-routing-wan.md)

# Skill และ tool ทั้งหมด

ทุก tool ด้านล่างเป็น **read-only** (`readOnlyHint=true`) ไม่ต้องใช้ credential ไม่ออกเครือข่าย

## subnet-calculator  · server `subnet-calc` · v0.1.0

| Tool | พารามิเตอร์ | ผลลัพธ์ |
|---|---|---|
| `subnet_calculator` | `cidr` (IPv4) | network, broadcast, netmask, wildcard, usable, first/last host, previous/next, classification, ตัวอย่าง host ≤ 10 |
| `subnet_calculator_v6` | `cidr` (IPv6) | ช่วง, จำนวน /64, previous/next, classification, หมายเหตุการจัดสรร (/64 LAN, /48 site …) |
| `subnet_calculator_auto` | `cidr` | เลือก v4/v6 อัตโนมัติ |
| `same_subnet` | `ip_a`, `ip_b`, `prefix` | อยู่ subnet เดียวกันหรือไม่ พร้อม subnet ของแต่ละฝั่ง |

กฎ input: ต้องเป็น canonical network (`address/prefix` ไม่มี host bits ไม่มี zone ของ IPv6 ไม่ใช้รูป netmask) ถ้าผิดจะ error ไม่แก้ให้เงียบ ๆ

Classification ที่รู้จัก: documentation (RFC 5737/3849), private (RFC 1918), shared/CGNAT 100.64.0.0/10 (RFC 6598), reserved 240.0.0.0/4, this-network 0.0.0.0/8, link-local, loopback, multicast, global

## fwrule-analyzer  · server `fwrule` · v1.1.0 (นำเข้าจาก NetClaw)

| Tool | หน้าที่ |
|---|---|
| `parse_policy` | แปลง config ของ vendor เป็น JSON กลาง เพื่อตรวจจำนวน rule และ object |
| `analyze_firewall_rule_overlap` | เทียบ rule ผู้สมัครกับ rule เดิมใน 6 มิติ (zone, address, port, protocol, action, application) ตรวจ overlap / shadow / conflict / duplicate |
| `batch_analyze_overlap` | เหมือนกันแต่หลาย rule ผู้สมัครในครั้งเดียว (รับ JSON ที่ normalize แล้ว) |
| `list_supported_vendors` | รายชื่อ vendor ที่รองรับและรูปแบบ config |

Server มาจาก AutomateIP/fwrule-mcp commit `3bd52d79` ล็อกเวอร์ชันแล้ว ห่อด้วย launcher ของเราที่ใส่ `readOnlyHint` และจะหยุดทำงานถ้า upstream เพิ่ม tool ที่ยังไม่ได้รีวิว รายละเอียดรีวิว: `docs/imports/fwrule-analyzer.md`

## ที่ตั้งใจไม่ import (ยัง)

| จาก NetClaw | เหตุผล |
|---|---|
| `multivendor-cli` | ตัวกรอง read-only มีช่องโหว่ (pipe `redirect/tee/append` ผ่านได้) และมี `apply_config` |
| `syslog` | bind `0.0.0.0` โดยปริยาย ไม่มี auth/TLS |
| gNMI (`gnmi_set`) | มี tool เขียน และด่าน change request ข้ามได้ด้วยโหมด lab |
| ทุก tool ที่เขียน config | รอด่านอนุมัติฝั่ง server (P4) |

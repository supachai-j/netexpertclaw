# netpaw — คู่มือใช้งาน

**netpaw** คือชุด skill และ MCP tool สำหรับวิศวกรเครือข่าย เขียนครั้งเดียวแล้วใช้ได้กับ 5 agent runtime: **Claude Code, Codex, Hermes Agent, OpenClaw, thClaws**

แนวคิดมาจาก [NetClaw](https://github.com/automateyournetwork/netclaw) (Apache-2.0) แต่เราไม่ fork ทั้งก้อน เลือก import ทีละ skill ผ่านสคริปต์ที่ pin commit และผ่านการรีวิวความปลอดภัยก่อน

## สถานะปัจจุบัน (ตรงตามหลักฐาน)

| เรื่อง | สถานะ |
|---|---|
| Skill ที่ใช้ได้ | `subnet-calculator` (คำนวณ subnet), `fwrule-analyzer` (วิเคราะห์ rule firewall ซ้อนทับ/shadow) |
| ทั้งสองตัว | **read-only** ไม่แตะอุปกรณ์ ไม่ใช้ credential |
| Claude Code, Hermes | ทดสอบกับ runtime จริงแล้ว (Claude Code ทดสอบกับโมเดลจริง) |
| Codex, OpenClaw, thClaws | ทดสอบเส้นทาง runtime → MCP ด้วยโมเดลจำลอง ยังไม่ได้ทดสอบกับโมเดลจริง ; `fwrule-analyzer` ใช้ได้บน OpenClaw และ thClaws แต่ **ยังไม่ขึ้นใน Codex** (กำลังวินิจฉัย) |
| Skill ที่เขียน config อุปกรณ์ | **ยังไม่มี** ตั้งใจเลื่อนไปจนกว่าจะมีด่านอนุมัติฝั่ง server (ดูหน้า [ความปลอดภัย](safety.html)) |

> อย่าอ่านตารางข้างบนเป็น "รองรับครบ" — ดูรายละเอียดและข้อจำกัดที่หน้า [ความเข้ากันได้](compat.html)

## อ่านอะไรก่อน

1. [ติดตั้ง](install.html) — เลือก runtime ที่คุณใช้
2. [วิธีใช้](using.html) — ตัวอย่างคำสั่งถาม agent และผลลัพธ์จริง
3. [Skill ทั้งหมด](skills.html) — รายการ tool และพารามิเตอร์
4. [ความปลอดภัย](safety.html) — สิ่งที่ควรรู้ก่อนใช้กับเครือข่ายจริง
5. [พัฒนา/เพิ่ม skill](develop.html) — สำหรับทีมที่จะต่อยอด
6. [แก้ปัญหา](troubleshoot.html)

## ข้อควรระวังเรื่องข้อมูล

- ตัวอย่างทั้งหมดใช้ IP ช่วง documentation (192.0.2.0/24, 2001:db8::/32) อย่าใส่ข้อมูลลูกค้าจริงลงใน skill, ตัวอย่าง หรือไฟล์ที่ commit
- config firewall ที่ส่งให้ `fwrule-analyzer` ผ่าน LLM อาจมีข้อมูลอ่อนไหว ให้ทำ sanitize ก่อน (PDPA)

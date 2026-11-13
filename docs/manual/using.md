# วิธีใช้

ไม่ต้องจำชื่อ tool บอก agent ว่าต้องการอะไรเป็นภาษาธรรมดา agent จะเลือก skill ตามคำอธิบายแล้วเรียก tool เอง (ชื่อ tool ต่างกันตาม runtime — Codex: `mcp__subnet_calc`, thClaws: `subnet-calc__same_subnet`, OpenClaw: ผ่าน `tool_search`)

> ผลด้านล่างมาจากการเรียก tool จริง แต่ **การที่โมเดลจริงเลือก skill เองได้ดีแค่ไหน** ทดสอบแล้วเฉพาะ Claude Code

## 1. คำนวณ subnet (`subnet-calculator`)

**ถาม:** "ขอรายละเอียดของ 192.0.2.0/26 รวม wildcard mask สำหรับ ACL"

**ผลที่ tool คืน (ตัดบางส่วน):**

| ฟิลด์ | ค่า |
|---|---|
| network / broadcast | 192.0.2.0 / 192.0.2.63 |
| netmask / wildcard | 255.255.255.192 / 0.0.0.63 |
| usable hosts | 62 (192.0.2.1 – 192.0.2.62) |
| previous / next | 192.0.1.192/26 / 192.0.2.64/26 |
| classification | documentation (RFC 5737/3849) |

ใช้ใน ACL: `permit ip 192.0.2.0 0.0.0.63 any`

**ถาม:** "2001:db8::/48 มี /64 กี่ก้อน" → ตอบ **65,536** และระบุว่าเป็น site allocation

**ถาม:** "192.0.2.10 กับ 192.0.2.70 อยู่ subnet เดียวกันไหมที่ /26" → **ไม่** (192.0.2.0/26 กับ 192.0.2.64/26)

**ป้อน input ผิด:** ถ้าส่ง `192.0.2.5/26` (มี host bits) tool ปฏิเสธและ agent ควรแนะนำ `192.0.2.0/26` แทน ไม่เดาให้เงียบ ๆ

### สูตรที่ใช้บ่อย
- **ลิงก์ point-to-point:** IPv4 /30 (2 usable) หรือ /31 (RFC 3021) ; IPv6 /127 (RFC 6164)
- **VLSM:** บอกความต้องการเป็นรายการ (เช่น Eng 500 host, Sales 100, Mgmt 10) agent จะเรียงจากใหญ่ไปเล็ก เลือก prefix ที่เล็กที่สุดที่พอ แล้วทำตารางแผนที่อยู่ ตรวจแต่ละก้อนด้วย tool
- **IPv6 site:** /48 ต่อ site, /64 ต่อ VLAN

## 2. วิเคราะห์ rule firewall (`fwrule-analyzer`)

ใช้ตรวจ rule ใหม่ก่อนเพิ่ม (ซ้อนทับ, ถูกบัง, ขัดแย้ง, ซ้ำ) หรือ audit ทั้ง policy รองรับ PAN-OS, ASA, FTD, IOS/IOS-XE, IOS-XR, Check Point, SRX, Junos, Nokia SR OS, FortiOS

**ถาม:** "ตรวจว่า rule ใหม่นี้ถูก rule เดิมบังไหม — เดิม: deny tcp 443 จาก 10.0.0.0/8 ไป 192.0.2.0/24 ; ใหม่: permit tcp 443 จาก 10.1.0.0/16 ไป 192.0.2.10/32"

**ผลจริง:** `overlap_type: shadowed`, severity `critical` — rule ใหม่ (permit) ถูก rule เดิม (deny) ซึ่งอยู่ก่อนและครอบคลุมกว่าบังทั้งหมด จึงไม่มีวันถูกใช้ ทั้ง source และ destination เป็น subset

**ลำดับที่แนะนำ:**

1. `parse_policy` แปลง config ของ vendor เป็น JSON กลาง ตรวจจำนวน rule และ object ที่ resolve
2. `analyze_firewall_rule_overlap` (หรือ `batch_analyze_overlap` ถ้ามีหลาย rule) ตรวจ rule ใหม่กับ policy
3. สรุปผล: อนุมัติ / แก้ / ปฏิเสธ — **การอนุมัติและการแก้บนอุปกรณ์ทำโดยคน** skill นี้ไม่แก้ firewall
4. ถ้า parser ของ vendor ให้ผลแปลก ให้ส่งเป็น JSON ที่ normalize แล้วแทน (Mode 2)

> พึงระวัง: parser เป็น best-effort ตรวจผลที่ได้เทียบกับ config จริงเสมอ และ sanitize config ก่อนส่งเข้า LLM

## เรียกตรงจากบรรทัดคำสั่ง (ไม่ผ่าน agent)

ใช้ทดสอบ MCP server เองได้ด้วย stdio client:

```bash
uv run --no-project --isolated --with mcp==1.30.0 python tests/smoke_mcp.py
```

## ใช้ใน automation / headless

- Codex `exec`: tool read-only ทำงานได้ (มี annotation) ; tool แบบเขียน (ในอนาคต) จะถูกบล็อกถ้าไม่มีคนอนุมัติ
- thClaws `-p` และ OpenClaw `agent --local` **ไม่ถามอนุมัติ** สำหรับ MCP tool ที่เคยอนุมัติไว้ ดังนั้นอย่าต่อ tool ที่แก้อุปกรณ์เข้ากับโหมดเหล่านี้ (ดู [ความปลอดภัย](safety.html))

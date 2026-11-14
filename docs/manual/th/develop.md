# พัฒนา / เพิ่ม skill

## โครงสร้าง repo

```
skills/<name>/SKILL.md     # ต้นฉบับ (runtime-neutral)
mcp/servers.json           # registry ของ MCP server  ({root} = path ติดตั้ง)
mcp/<server>/              # โค้ด server ของเรา หรือ launcher + requirements ที่ pin
imports/netclaw.json       # รายการ import จาก NetClaw (pin commit)
scripts/                   # build.py, lint.py, import-netclaw.py, common.py
tests/                     # unit, security regression, smoke MCP, runtimes/
docs/                      # แผน, รีวิวความปลอดภัย, conformance, manual
dist/                      # ผลลัพธ์ build (ไม่ commit)
```

## Frontmatter ของ skill

```yaml
---
name: my-skill              # = ชื่อโฟลเดอร์ ตัวพิมพ์เล็ก/ขีด
description: ประโยคเดียว บอกว่าทำอะไรและควรใช้เมื่อไร (≤ 1024 ตัวอักษร)
license: Apache-2.0
metadata:
  version: "0.1.0"
  risk: read                # read | write
  mcp_servers: "subnet-calc"   # ชื่อใน mcp/servers.json
  requires_bins: "uv"
---
```

Key ระดับบนที่อนุญาต: `name, description, license, metadata, compatibility` เท่านั้น (ห้าม `allowed-tools`) ไฟล์ที่อยู่กับ skill ได้เฉพาะ `SKILL.md`, `references/*.md`, `agents/*.yaml`

skill แบบ `risk: write` ต้องมี `metadata.approval: required` และหัวข้อ `## Approval` ที่ระบุขั้นตอนจริง แต่อย่าเข้าใจผิดว่าพอแล้ว ด่านจริงต้องอยู่ใน server

เขียนชื่อ tool ตรง ๆ ใน SKILL.md **อย่าใส่ prefix ของ runtime** (`mcp__…`, `server__tool`) เพราะแต่ละ runtime ตั้งชื่อต่างกัน

## เพิ่ม MCP server ของเราเอง

1. เขียน server (FastMCP) ใส่ annotation: tool อ่าน → `ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)`; tool เขียน → **ห้าม** `readOnlyHint`
2. ลงทะเบียนใน `mcp/servers.json` พร้อม `capability` และ args แบบ `uv run --quiet --no-project --isolated --with mcp==<เวอร์ชันตรึง> python {root}/mcp/<name>/server.py`
3. `python3 scripts/lint.py` → `python3 -m unittest discover -s tests` → `uv run --with mcp==1.30.0 python tests/smoke_mcp.py`
4. `python3 scripts/build.py` แล้วทดสอบกับ runtime จริงตาม [ติดตั้ง](install.html)

## Import skill จาก NetClaw

```bash
python3 scripts/import-netclaw.py --upstream <checkout ของ netclaw ที่ commit cfafa46c>
```

สคริปต์ตรวจ commit, เอาเฉพาะ `SKILL.md`, แก้ข้อความแบบ exact-match (ถ้าต้นทางเปลี่ยนจะ fail), เขียน frontmatter ใหม่, บันทึก hash และรายการใน `NOTICE`, ตรวจ hash ของ requirements ทุก import ต้องมีเอกสารรีวิวใน `docs/imports/<skill>.md` และผ่านการตรวจความปลอดภัยก่อน merge ห้าม import server ทั้งตัวโดยไม่ตรวจรายชื่อ tool (ดู `docs/DECISIONS.md` D-1)

## การทดสอบ

| ชั้น | ทำอะไร |
|---|---|
| lint | schema, ชื่อ, server ที่อ้างถึง, symlink/ไฟล์แปลก, secret, NOTICE, LICENSE |
| unit | logic ของ tool + regression ของทุกข้อใน SECURITY-REVIEW |
| smoke MCP | spawn server ตาม `.mcp.json` จริง เรียก tool ผ่าน stdio ตรวจ annotation |
| runtime L1–L4 | skill เห็น → config รับ → runtime เปิด server → โมเดล (จำลอง) เรียก tool |

รายงานแต่ละ runtime ต้องบอกระดับที่ผ่านจริง อย่าเรียก runtime ที่ไม่ได้ทดสอบว่า "รองรับ"

## ถอดการติดตั้งบนเครื่องทดสอบ

ติดตั้งทุกอย่างของการทดสอบใน HOME แยกโฟลเดอร์เดียว (เช่น `~/nec-test`) จบงานแล้วลบโฟลเดอร์นั้น ห้ามคัดลอก credential ไปเครื่องทดสอบ

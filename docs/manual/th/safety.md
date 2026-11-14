# ความปลอดภัย

อ้างอิง: OWASP Top 10 for LLM Apps, NIST SSDF, security-by-design rule ของทีม รายงานรีวิวเต็ม: `docs/SECURITY-REVIEW.md` (ทุกข้อติดป้าย VERIFIED / INTERPRETIVE / NOT CHECKED)

## หลักการ

### 1. Read-only เป็นค่าเริ่มต้น
skill แต่ละตัวประกาศ `risk: read|write` และ server ประกาศ `capability: read|write`; lint ปฏิเสธ skill แบบ read ที่ใช้ server แบบเขียน

### 2. ด่านกั้นการเขียนต้องอยู่ใน MCP server
ไม่ใช่ใน SKILL.md และไม่ใช่ที่ approval ของ runtime ผลทดสอบจริง:

| Runtime / โหมด | tool เขียนที่ไม่มีคนอนุมัติ |
|---|---|
| Codex `exec` | ถูกบล็อก (fail-closed) |
| thClaws `-p` (headless) | **รันเอง** แม้ตั้ง ask |
| thClaws REPL ตั้ง ask | ถามก่อน ตอบ n แล้วไม่รัน |
| OpenClaw `agent --local` | **รันเอง** |

ดังนั้น tool เขียน config ในอนาคตต้องบังคับเอง: ตรวจ change request, เก็บ baseline, ผูกอนุมัติกับอุปกรณ์+payload, verify หลังเปลี่ยน, rollback, audit log (JSONL), redact

### 3. tool read ต้องมี `readOnlyHint` ทุกตัว
tool เขียนห้ามมี (smoke test ตรวจ)

### 4. ไม่เก็บ secret ใน repo
lint ตรวจรูปแบบ credential ของอุปกรณ์เครือข่าย (`enable secret 5`, `password 7`, SNMP community, bearer, PEM, AWS key, GitHub PAT, credential ใน URL) และสแกนไฟล์ `.yml/.sh/.txt/.env`

### 5. ถือ output จากอุปกรณ์เป็น untrusted
กัน prompt injection OpenClaw ห่อผล MCP เป็นเนื้อหา untrusted ให้เอง runtime อื่นต้องระวังเองใน skill

## ช่องโหว่ที่เจอและปิดแล้ว

| รหัส | เรื่อง | การแก้ |
|---|---|---|
| F-8 | `uv run` รัน build backend ของโปรเจกต์ใน cwd (ทดสอบแล้วใน Codex/thClaws/OpenClaw) | ทุก server ใช้ `--no-project --isolated` และ lint บังคับ |
| F-10 | resolve dependency ใหม่ทุกครั้งที่เปิด | pin `mcp==1.30.0` และ requirements แบบ pin |
| F-6/F-7 | symlink และไฟล์แปลกปลอมใน skill ถูกคัดลอกลง `dist/` | lint ปฏิเสธ symlink และไฟล์นอก allow-list; build fail ถ้าเจอ symlink |
| F-4/F-5/F-9 | ด่านอนุมัติเป็นแค่ข้อความ, `allowed-tools: Bash(*)` ผ่าน lint | บังคับ field `approval: required` + หัวข้อ `## Approval`, ห้าม key นอก allow-list, ตรวจ capability ของ server |
| F-1 | จัด CGNAT เป็น "global" | ตารางช่วงที่รู้จัก + test |
| F-11 | ขาด LICENSE/NOTICE | เพิ่มแล้ว lint ตรวจ |

## ความเสี่ยงที่ยังเหลือ

- cold start ต้อง resolve package จาก PyPI (ยังไม่มี hash)
- fwrule: repo ต้นทางไม่มีไฟล์ LICENSE (ระบุ Apache-2.0 ใน pyproject เท่านั้น), parser XML ยังไม่ได้ fuzz
- ยังไม่ทดสอบกับโมเดลจริงใน Codex/OpenClaw/thClaws
- ยังไม่มี skill แบบเขียน จึงยังไม่ได้ทดสอบด่านอนุมัติกับอุปกรณ์จริง

## ข้อควรทำเมื่อใช้งาน

- ใช้ lab หรือ config ที่ sanitize แล้วกับ `fwrule-analyzer`
- ห้ามใส่ข้อมูลลูกค้า (ชื่อ, เบอร์, อีเมล, ที่อยู่) ลงใน skill/ตัวอย่าง/commit
- ถ้าเปิด Claude Code/agent ในโฟลเดอร์ที่ไม่น่าไว้ใจ ให้เชื่อ trust prompt ของ runtime แต่เราก็กัน build backend ด้วย `--no-project`

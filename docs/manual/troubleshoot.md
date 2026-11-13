# แก้ปัญหา

| อาการ | สาเหตุที่พบ | วิธีแก้ |
|---|---|---|
| MCP ขึ้น `failed` ครั้งแรก | ต้องดึง package จากอินเทอร์เน็ต หรือไม่มี `uv` | ตรวจ `uv --version` และการเชื่อมต่อ ; รันคำสั่งใน `dist/<runtime>/…snippet` ด้วยมือเพื่อดู error |
| Codex ตอบว่า `MCP tool call requires approval, but approval policy is never` | tool ไม่มี `readOnlyHint` (หรือเป็น tool เขียน) | ตรวจ annotation ด้วย `tests/smoke_mcp.py` ; `subnet-calc` ทดสอบแล้วว่าผ่าน ; `fwrule` บน Codex ดู [ความเข้ากันได้](compat.html) |
| thClaws `mcp spawn refused … not in the user allowlist` | เปลี่ยน args/โฟลเดอร์ หรือรัน headless ครั้งแรก | เปิด REPL แล้วอนุมัติ (`y`) ใหม่ |
| OpenClaw ไม่เห็น tool ตรง ๆ | พฤติกรรมของ OpenClaw | ให้โมเดลใช้ `tool_search` แล้ว `dispatch_action` |
| OpenClaw ลงแล้วได้เวอร์ชันเก่า | Node 22 | อัปเกรดเป็น Node ≥ 24.16 |
| Hermes `mcp_servers:` ซ้ำ | ต่อท้าย config ที่มีบล็อกอยู่แล้ว | merge ด้วยมือ |
| `subnet_calculator` ตอบ error `host bits set` | ใส่ `192.0.2.5/26` | ใช้ network address `192.0.2.0/26` |
| `tool list changed upstream; regenerate tools cache` (จาก proxy ของ fwrule) | tool list จริงไม่ตรงกับ `tools.cache.json` | ตั้งใจให้หยุด : รัน `scripts/gen_tools_cache.py fwrule`, ตรวจ diff ของ tool ที่เปลี่ยน แล้ว commit |
| `fwrule launcher: tool set changed` | upstream เพิ่ม/เปลี่ยน tool | ตั้งใจให้หยุด : ต้องรีวิว tool ใหม่ก่อน แล้วอัปเดต `REVIEWED` ใน `mcp/fwrule/launch.py` |
| lint: `uv run needs --no-project --isolated …` | server entry ไม่ตรงกฎ | ใช้รูปแบบใน [พัฒนา](develop.html) |
| `dist/` มี path ผิดเครื่อง | build ด้วย `--root` เดิม | build ใหม่ด้วย `--root` ของเครื่องนั้น |

ยังแก้ไม่ได้: เปิด issue ใน repo พร้อมคำสั่งและ output จริง ห้ามแนบข้อมูลลูกค้าหรือ credential

## ถอน thClaws แล้ว allowlist ยังอยู่
`netpaw uninstall` ถอน skill และรายการใน `.thclaws/mcp.json` แต่ไม่แตะ `~/.config/thclaws/mcp_allowlist.json` (เป็นไฟล์ของ thClaws เอง) ลบรายการ netpaw ออกเองถ้าต้องการ

## ไฟล์ `*.bak-netpaw`
`--with-mcp` สำรอง config เดิมไว้ 1 ไฟล์ต่อไฟล์ (สถานะก่อน netpaw แตะครั้งแรก, สิทธิ์ 0600) config ของ runtime อาจมีความลับ จึงลบไฟล์สำรองทิ้งเมื่อไม่ต้องใช้แล้ว

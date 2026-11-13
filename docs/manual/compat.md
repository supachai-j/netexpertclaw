# ความเข้ากันได้ (ผลทดสอบจริง)

ระดับ: **L1** เห็น skill · **L2** config ถูกรับ · **L3** runtime เปิด server และเห็น tool · **L4** โมเดลสั่งเรียก tool ผ่าน runtime แล้วได้ผลจริง

| Runtime | เวอร์ชันที่ทดสอบ | ระดับที่ผ่าน | โมเดล |
|---|---|---|---|
| Claude Code | 2.1.322 | L1–L4 | โมเดลจริง |
| Hermes Agent | v0.23.1 | L1–L3 | ไม่ได้รัน L4 |
| Codex CLI | 0.169.0 | L1–L4 | จำลอง (127.0.0.1) |
| thClaws | 0.156.0 | L1–L4 | จำลอง |
| OpenClaw | 2026.11.3 | L1–L4 | จำลอง |

**ขอบเขตของผลทดสอบ:** Claude Code ทดสอบทั้ง 2 skill (init event เห็น server `subnet-calc` และ `fwrule` เป็น `connected`) OpenClaw ผ่าน L1–L4 ทั้ง 2 skill, thClaws ผ่าน L3–L4 ของ `fwrule` (อนุมัติ MCP 2 ครั้งเพราะมี 2 server), Codex ผ่าน L4 ของ `subnet-calculator` แต่ **`fwrule` ไม่ถูกลงทะเบียนใน Codex 0.169.0** (config รับ, handshake ผ่าน แต่ session ไม่เห็น tool ของ fwrule; ยังไม่ทราบสาเหตุ — ถือว่า `fwrule` บน Codex ยังไม่รองรับจนกว่าจะวินิจฉัย) Hermes ทดสอบกับ `subnet-calculator` เท่านั้น

L4 ด้วยโมเดลจำลองพิสูจน์เส้นทาง runtime → MCP เท่านั้น **ไม่ได้พิสูจน์** ว่า LLM จริงเลือก tool เองหรือทำตามข้อความใน SKILL.md การทดสอบกับโมเดลจริงต้องให้เจ้าของล็อกอินบนเครื่องทดสอบเอง (ห้ามคัดลอก token)

ทดสอบบน Ubuntu 24.04 x86_64 เท่านั้น ยังไม่ได้ลอง Windows/macOS

## ข้อควรรู้ต่อ runtime

| Runtime | ข้อควรรู้ |
|---|---|
| Codex | ชื่อ tool เป็น namespace `mcp__<server>` (ขีดกลางกลายเป็น `_`) ; `exec` ปฏิเสธ tool ที่ไม่มี `readOnlyHint` ; ผลของ `agents/openai.yaml` ยังไม่ได้ตรวจ |
| OpenClaw | ต้อง Node ≥ 24.16 (Node 22 จะได้เวอร์ชันเก่าเงียบ ๆ) ; `mcp set` รับ object ของ server เดียว ไม่ใช่ `{"mcpServers":…}` ; โมเดลต้อง `tool_search` แล้ว `dispatch_action` |
| thClaws | อนุมัติ MCP ผูกกับ command line ทั้งบรรทัด + cwd (เอกสารว่า `command` อย่างเดียว) ; `-p` ไม่รัน slash command ; `--cli` บน Linux ไม่มี GUI ต้องมี libwebkit2gtk-4.1 |
| Hermes | ลงจาก pip/git ไม่ได้ ใช้ installer ทางการ ; merge `mcp_servers:` เอง |
| Claude Code | เปิดในโฟลเดอร์ repo จะเห็น server `failed` จาก `.mcp.json` ที่ root (ไม่กระทบ plugin) |

หลักฐานดิบ คำสั่ง และ output: `docs/CONFORMANCE.md`

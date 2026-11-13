# ติดตั้ง

ต้องมี **`uv`** (https://docs.astral.sh/uv/) และ Python 3 ในเครื่อง MCP server ถูกเรียกผ่าน `uv run --no-project --isolated` ครั้งแรกที่รันต้องต่ออินเทอร์เน็ตเพื่อดึง package (ตรึงเวอร์ชันไว้แล้ว)

repo เป็น **private** (`supachai-j/netexpertclaw`) ต้องมีสิทธิ์ git เข้าถึงก่อน อย่าคัดลอก token ไปวางบนเครื่อง worker ให้ส่ง tarball ของ commit ที่ต้องการแทน

## คำสั่ง `netpaw` (codename ของแพ็กเกจ)

`bin/netpaw` เป็น CLI ตัวเดียวห่อสคริปต์ทั้งหมด (stdlib ล้วน):

```bash
bin/netpaw doctor                       # เช็กว่ามี uv, python3 และ runtime อะไรบ้าง
bin/netpaw list                         # skill ที่มี พร้อม risk และ capability ของ server
bin/netpaw install hermes --root "$PWD" # ดูแผนติดตั้ง (dry run ไม่เขียนอะไร)
bin/netpaw install hermes --root "$PWD" --apply   # คัดลอกเฉพาะโฟลเดอร์ skill (ไม่แตะ config)
bin/netpaw build | lint | test | smoke | site | import
```

`install --apply` คัดลอก skill ให้เฉพาะ Codex และ Hermes ส่วน config ของ MCP **พิมพ์ให้แล้วคุณ merge เอง** เสมอ ไม่มีการอ่านหรือเขียน credential ทั้ง Claude Code, OpenClaw และ thClaws ให้ทำตามขั้นตอนด้านล่าง

> `bin/netpaw` ไม่ถูกใส่ลง PATH ให้อัตโนมัติ เรียกด้วย path เต็มหรือสร้าง alias เอง (เช่น `alias netpaw=~/netexpertclaw/bin/netpaw`)

## ขั้นตอนทั่วไป (ทุก runtime ยกเว้น Claude Code plugin)

```bash
git clone https://github.com/supachai-j/netexpertclaw.git ~/netexpertclaw
cd ~/netexpertclaw
python3 scripts/build.py --root "$PWD"      # สร้างไฟล์ของแต่ละ runtime ลง dist/
python3 scripts/lint.py                     # ตรวจ skill + MCP registry
```

`--root` คือ path ที่ repo อยู่บนเครื่องที่จะรัน (ถูกแทนลงใน config ของ MCP) ถ้าย้าย repo ต้อง build ใหม่

## Claude Code

ทดสอบแล้ว: โหลดจากโฟลเดอร์

```bash
claude --plugin-dir ~/netexpertclaw
```

ผลที่ควรเห็น: skill `netexpertclaw:subnet-calculator`, `netexpertclaw:fwrule-analyzer` และ MCP `plugin:netexpertclaw:subnet-calc`, `plugin:netexpertclaw:fwrule` สถานะ `connected`

แบบ marketplace (ยังไม่ได้ทดสอบกับ repo private):

```
/plugin marketplace add supachai-j/netexpertclaw
/plugin install netexpertclaw --marketplace supachai-j/netexpertclaw
```

> ถ้าเปิด Claude Code *ในโฟลเดอร์ repo นี้เอง* จะเห็น server ตัวหนึ่งขึ้น `failed` เพราะอ่าน `.mcp.json` ที่ root เป็น project server (`${CLAUDE_PLUGIN_ROOT}` ยังไม่ถูกแทนค่า) ตัว plugin ปกติ ไม่กระทบ

## Hermes Agent

ทดสอบแล้ว (Hermes v0.23.1)

```bash
mkdir -p ~/.hermes/skills
cp -r dist/hermes/skills/netexpertclaw ~/.hermes/skills/
cat dist/hermes/mcp_servers.yaml.snippet     # นำไป merge ใน ~/.hermes/config.yaml
```

ถ้า `config.yaml` มีบล็อก `mcp_servers:` อยู่แล้ว ให้ **merge เอง** อย่าต่อท้ายซ้ำ ตรวจผล:

```bash
hermes skills list | grep -E 'subnet-calculator|fwrule-analyzer'
hermes mcp test subnet-calc        # ควรขึ้น Connected + Tools discovered: 4
hermes mcp test fwrule        # fwrule ยังไม่ได้ทดสอบบน Hermes
```

สคริปต์ทดสอบซ้ำได้: `tests/runtimes/hermes.sh` (ใช้บนเครื่องทดสอบที่แยก HOME เท่านั้น)

## Codex CLI

ทดสอบ L1–L4 ด้วยโมเดลจำลอง (Codex 0.169.0)

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -r dist/codex/skills/* "${CODEX_HOME:-$HOME/.codex}/skills/"
cat dist/codex/config.toml.snippet >> "${CODEX_HOME:-$HOME/.codex}/config.toml"   # ตรวจก่อนว่ายังไม่มี [mcp_servers.<ชื่อ>] ซ้ำ
codex debug prompt-input | grep -E 'subnet-calculator|fwrule-analyzer'
codex mcp get subnet-calc
```

> `fwrule-analyzer` บน Codex 0.169.0: server เชื่อมได้แต่ tool ไม่ถูกลงทะเบียนใน session ยังไม่ทราบสาเหตุ (ดู [ความเข้ากันได้](compat.html)) ใช้ `subnet-calculator` บน Codex ได้ตามปกติ

- Codex เรียก MCP tool เป็น namespace `mcp__subnet_calc` — ไม่ต้องพิมพ์ชื่อ tool เต็ม ให้บอกเป้าหมายเป็นภาษาธรรมดา
- tool ทุกตัวของเราติด `readOnlyHint` แล้ว ซึ่งจำเป็นต่อ `codex exec` (ถ้าไม่มี Codex จะปฏิเสธการเรียก)

## OpenClaw

ทดสอบด้วยโมเดลจำลอง (OpenClaw 2026.11.3 ต้องใช้ Node ≥ 24.16)

```bash
openclaw skills install dist/openclaw/skills/subnet-calculator
openclaw skills install dist/openclaw/skills/fwrule-analyzer
openclaw skills info subnet-calculator            # ควรเป็น Ready และ Visible to model: yes
# MCP: ใส่เฉพาะ "ตัว server" ไม่ใช่ทั้งก้อน {"mcpServers": ...}
python3 - <<'PY'
import json, subprocess
for name, cfg in json.load(open("dist/openclaw/mcp.json.snippet"))["mcpServers"].items():
    subprocess.run(["openclaw", "mcp", "set", name, json.dumps(cfg)], check=True)
PY
openclaw mcp probe                                 # ควรเห็น 4 tools ต่อ server
```

`openclaw skills install` จะพิมพ์ "gateway refresh failed, requires credentials" ถ้าไม่มี gateway — การติดตั้งยังสำเร็จตามปกติ

OpenClaw ไม่เปิด MCP tool ให้โมเดลโดยตรง โมเดลต้องค้นด้วย `tool_search` แล้วเรียกด้วย `dispatch_action` ผลจาก tool ถูกห่อเป็นเนื้อหา "ไม่น่าเชื่อถือ" ซึ่งเป็นพฤติกรรมที่ตั้งใจ

## thClaws

ทดสอบด้วยโมเดลจำลอง (thClaws 0.156.0)

```bash
# ในโฟลเดอร์โปรเจกต์ที่จะใช้งาน
cp -r dist/thclaws/.thclaws ./
thclaws          # เปิด REPL แล้วพิมพ์ /skills และ /mcp
```

บนเครื่อง Linux headless ที่จะใช้ `--cli` ต้องมี `libwebkit2gtk-4.1-0 libsoup-3.0-0 libjavascriptcoregtk-4.1-0` (apt) ก่อน

ครั้งแรก thClaws จะถามอนุมัติการรัน MCP stdio **ครั้งละ 1 server (ตอนนี้มี 2 server จึงถาม 2 ครั้ง)** (`Approve and remember? [y/N]`) การอนุมัติผูกกับ **command line ทั้งบรรทัดและ cwd** เปลี่ยน args หรือย้ายโฟลเดอร์ต้องอนุมัติใหม่ และโหมด headless (`-p`) จะปฏิเสธถ้ายังไม่เคยอนุมัติ

## ตรวจว่าใช้ได้จริง

ถามแบบนี้แล้วดูว่า agent เรียก tool: "192.0.2.10 กับ 192.0.2.70 อยู่ subnet เดียวกันไหมที่ /26" ต้องได้คำตอบว่า **ไม่** (192.0.2.0/26 กับ 192.0.2.64/26) ดู [วิธีใช้](using.html)

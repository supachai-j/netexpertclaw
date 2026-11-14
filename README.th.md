# netpaw (ภาษาไทย)

**ชุด skill สำหรับงานวิศวกรรมเครือข่าย ใช้ได้กับ AI agent หลายตัว** เขียนครั้งเดียวเป็น [Agent Skills](https://agentskills.io) (ไฟล์ `SKILL.md` มาตรฐานเปิด) คู่กับ MCP tool แล้วติดตั้งลง Claude Code, Codex, Hermes Agent, OpenClaw และ thClaws จากต้นฉบับเดียว โอเพนซอร์ส Apache-2.0

> สถานะ: pre-release ทุก skill เป็น `experimental` อ่านเกณฑ์ที่ [docs/READINESS.md](docs/READINESS.md) เอกสารหลักเป็นภาษาอังกฤษที่ [README.md](README.md) หน้านี้สรุปให้เร็ว

## มีอะไรบ้าง
- `subnet-calculator` คำนวณ subnet IPv4/IPv6, wildcard mask, VLSM, ตรวจว่าอยู่ subnet เดียวกันไหม
- `fwrule-analyzer` หา rule firewall ที่ถูกบัง ซ้อนทับ ขัดกัน หรือซ้ำ หลายยี่ห้อ
- `rfc-lookup` ค้นและอ่าน RFC จาก rfc-editor.org พร้อมอ้างอิง
- `eve-lab-topology-design` ออกแบบและตรวจโครงสร้าง lab EVE-NG จากข้อความไฟล์ `.unl`
- `wikipedia-research` หาพื้นหลังและประวัติของโปรโตคอลจาก Wikipedia พร้อมแหล่งที่มา

ทุก tool **อ่านอย่างเดียว** ไม่ใช้ credential และไม่แก้อุปกรณ์ skill ที่ใช้อินเทอร์เน็ต (`rfc-lookup`, `wikipedia-research`) ออกได้ที่ host เดียวที่ประกาศไว้

## เริ่มใช้
```bash
git clone https://github.com/supachai-j/netpaw.git && cd netpaw
bin/netpaw doctor
bin/netpaw install -a codex -p standard --root "$PWD"                      # dry run
bin/netpaw install -a codex -p standard --root "$PWD" --with-mcp --apply   # ติดตั้งจริง
```
`netpaw install` เป็น dry run ถ้าไม่ใส่ `--apply` และถอนคืนได้ด้วย `netpaw uninstall --apply` ต้องมี `uv` ทดสอบบน Ubuntu 24.04 เท่านั้น **ไม่มี** `pip install netpaw` หรือ `npx netpaw` ติดตั้งจาก repo นี้เท่านั้น

## คู่มือภาษาไทย
หน้าเก่าที่ยังเก็บไว้อยู่ที่ [docs/manual/th/](docs/manual/th/) (บางหน้าอาจตามไม่ทัน เอกสารภาษาอังกฤษถือเป็นต้นฉบับ) เว็บคู่มือ: https://supachai-j.github.io/netpaw-docs/

## ร่วมพัฒนา
อ่าน [CONTRIBUTING.md](CONTRIBUTING.md) ใช้ IP ช่วง documentation เท่านั้น ห้ามใส่ข้อมูลลูกค้าหรือ credential รายงานช่องโหว่ตาม [SECURITY.md](SECURITY.md)

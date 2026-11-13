#!/usr/bin/env python3
"""Local MOCK model endpoint for L4 conformance (stdlib, 127.0.0.1 only, no credentials, no cloud).

Turn 1 (no tool result in the request): answer with ONE tool call to the first advertised tool whose name
ends with `same_subnet`, arguments fixed. Turn 2 (tool result present): answer with a text that quotes the result.
Speaks: OpenAI Responses (/v1/responses), OpenAI Chat Completions (/v1/chat/completions),
Anthropic Messages (/v1/messages). Logs a one-line summary per request to MOCK_LOG (no bodies kept except tool names).
usage: mock_model.py [port]
"""
import json, os, sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 9911
LOG = os.environ.get("MOCK_LOG", "/tmp/mock_model.log")
ARGS = json.loads(os.environ.get("MOCK_ARGS", '{"ip_a": "192.0.2.10", "ip_b": "192.0.2.20", "prefix": 24}'))
PICK = os.environ.get("MOCK_PICK", "same_subnet")

def log(s):
    with open(LOG, "a") as f:
        f.write("%s %s\n" % (time.strftime("%H:%M:%S"), s))

def tool_names(body):
    out = []
    for t in body.get("tools") or []:
        n = t.get("name") or (t.get("function") or {}).get("name")
        if n: out.append(n)
        for sub in (t.get("tools") or []):  # namespaced tool groups
            m = sub.get("name")
            if m: out.append(((n or "") + "." + m) if n else m)
    return out

def pick(names):
    for n in names:
        if n.endswith(PICK):
            return n
    return None

def has_result(body, kind):
    s = json.dumps(body.get("input") or body.get("messages") or [])
    if kind == "responses": return '"function_call_output"' in s
    if kind == "chat": return '"role": "tool"' in s
    return '"tool_result"' in s

def last_result_text(body):
    for it in reversed(body.get("input") or []):
        if isinstance(it, dict) and it.get("type") == "function_call_output":
            return json.dumps(it.get("output"))[:300]
    for m in reversed(body.get("messages") or []):
        if isinstance(m, dict) and m.get("role") == "tool":
            return json.dumps(m.get("content"))[:1800]
        if isinstance(m, dict) and isinstance(m.get("content"), list):
            for c in m["content"]:
                if isinstance(c, dict) and c.get("type") == "tool_result":
                    return json.dumps(c.get("content"))[:300]
    return ""

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _sse(self, events):
        self.send_response(200); self.send_header("Content-Type", "text/event-stream"); self.send_header("Cache-Control", "no-cache"); self.end_headers()
        for ev, data in events:
            self.wfile.write(("event: %s\ndata: %s\n\n" % (ev, json.dumps(data))).encode() if ev else ("data: %s\n\n" % (data if isinstance(data, str) else json.dumps(data))).encode())
            self.wfile.flush()
    def _json(self, code, obj):
        b = json.dumps(obj).encode(); self.send_response(code); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        log("GET %s" % self.path)
        if self.path.rstrip("/").endswith("/models"):
            return self._json(200, {"object": "list", "data": [{"id": "mock", "object": "model"}], "models": [{"slug": "mock"}]})
        self._json(404, {"error": "mock: not found"})
    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0); body = json.loads(self.rfile.read(n) or b"{}")
        p = self.path.split("?")[0]; names = tool_names(body); tn = pick(names)
        kind = "responses" if p.endswith("/responses") else "chat" if p.endswith("/chat/completions") else "anthropic" if p.endswith("/messages") else None
        log("POST %s kind=%s tools=%d same_subnet_tool=%s result_present=%s auth_hdr=%s names=%s" % (p, kind, len(names), tn, kind and has_result(body, kind), "yes" if self.headers.get("Authorization") or self.headers.get("x-api-key") else "no", ",".join(names)[:600]))
        if kind is None: return self._json(404, {"error": "mock: unsupported path"})
        if os.environ.get("MOCK_DUMP") and not os.path.exists(os.environ["MOCK_DUMP"]):
            json.dump([t for t in body.get("tools", []) if "tool_" in json.dumps(t)[:80] or "dispatch" in json.dumps(t)[:80]], open(os.environ["MOCK_DUMP"], "w"), indent=1)
        done = has_result(body, kind)
        seq = json.loads(os.environ.get("MOCK_SEQ", "[]"))
        if seq and kind == "chat":
            k = sum(1 for m in body.get("messages", []) if isinstance(m, dict) and m.get("role") == "tool")
            log("seq step %d/%d last_result=%s" % (k, len(seq), last_result_text(body)[:1800]))
            if k < len(seq):
                nm, ar = seq[k]
                d = [{"choices": [{"index": 0, "delta": {"role": "assistant", "tool_calls": [{"index": 0, "id": "call_%d" % k, "type": "function", "function": {"name": nm, "arguments": json.dumps(ar)}}]}, "finish_reason": None}]}, {"choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}]}]
            else:
                d = [{"choices": [{"index": 0, "delta": {"role": "assistant", "content": "MOCK-FINAL: seq done -> " + last_result_text(body)}, "finish_reason": None}]}, {"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}]
            return self._sse([(None, x) for x in d] + [(None, "[DONE]")])
        txt = "MOCK-FINAL: tool result received -> " + last_result_text(body)
        if kind == "responses":
            if done or not tn:
                msg = {"type": "message", "id": "msg_1", "role": "assistant", "content": [{"type": "output_text", "text": txt if done else "MOCK-FINAL: no same_subnet tool advertised; tools=%s" % names[:20]}]}
                return self._sse([("response.created", {"type": "response.created", "response": {"id": "r1"}}), ("response.output_item.done", {"type": "response.output_item.done", "item": msg}), ("response.completed", {"type": "response.completed", "response": {"id": "r1", "output": [msg], "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2}}})])
            fc = {"type": "function_call", "id": "fc_1", "call_id": "call_1", "name": tn, "arguments": json.dumps(ARGS)}
            if "." in tn:  # namespaced tool group (Codex: namespace `mcp__<server>`, name `<tool>`)
                fc["namespace"], fc["name"] = tn.split(".", 1)
            return self._sse([("response.created", {"type": "response.created", "response": {"id": "r1"}}), ("response.output_item.done", {"type": "response.output_item.done", "item": fc}), ("response.completed", {"type": "response.completed", "response": {"id": "r1", "output": [fc], "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2}}})])
        if kind == "chat":
            if done or not tn:
                d = [{"choices": [{"index": 0, "delta": {"role": "assistant", "content": txt if done else "MOCK-FINAL: no tool"}, "finish_reason": None}]}, {"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}]
            else:
                d = [{"choices": [{"index": 0, "delta": {"role": "assistant", "tool_calls": [{"index": 0, "id": "call_1", "type": "function", "function": {"name": tn, "arguments": json.dumps(ARGS)}}]}, "finish_reason": None}]}, {"choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}]}]
            return self._sse([(None, x) for x in d] + [(None, "[DONE]")])
        # anthropic messages (streaming)
        if body.get("stream") is not True:
            blocks = [{"type": "text", "text": txt}] if (done or not tn) else [{"type": "tool_use", "id": "toolu_1", "name": tn, "input": ARGS}]
            return self._json(200, {"id": "m1", "type": "message", "role": "assistant", "model": "mock", "content": blocks, "stop_reason": "end_turn" if (done or not tn) else "tool_use", "usage": {"input_tokens": 1, "output_tokens": 1}})
        ev = [("message_start", {"type": "message_start", "message": {"id": "m1", "type": "message", "role": "assistant", "model": "mock", "content": [], "usage": {"input_tokens": 1, "output_tokens": 1}}})]
        if done or not tn:
            ev += [("content_block_start", {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}}), ("content_block_delta", {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": txt}}), ("content_block_stop", {"type": "content_block_stop", "index": 0}), ("message_delta", {"type": "message_delta", "delta": {"stop_reason": "end_turn"}, "usage": {"output_tokens": 1}})]
        else:
            ev += [("content_block_start", {"type": "content_block_start", "index": 0, "content_block": {"type": "tool_use", "id": "toolu_1", "name": tn, "input": {}}}), ("content_block_delta", {"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": json.dumps(ARGS)}}), ("content_block_stop", {"type": "content_block_stop", "index": 0}), ("message_delta", {"type": "message_delta", "delta": {"stop_reason": "tool_use"}, "usage": {"output_tokens": 1}})]
        ev.append(("message_stop", {"type": "message_stop"}))
        self._sse(ev)

if __name__ == "__main__":
    log("mock up on 127.0.0.1:%d" % PORT)
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()

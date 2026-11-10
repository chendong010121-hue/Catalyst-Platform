"""Loopback-only local UI for live runs, history replay, and result viewing."""

from __future__ import annotations

import base64
import binascii
import secrets
import re
import os
import hashlib
import json
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, unquote, urlsplit

from .observability import RunRecorder
from .trace_log import JsonlTraceStore


_MAX_BODY_BYTES = 1_048_576
_MAX_MESSAGE_CHARS = 20_000
_MAX_PATH_CHARS = 4_096


def _read_saved_result(path: Path | None):
    if path is None:
        return None
    # On Windows the reader can briefly race the writer's atomic replacement.
    for attempt in range(3):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except PermissionError:
            if attempt == 2:
                raise
            time.sleep(0.02)


_PAGE = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="default-src 'self'; connect-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'">
  <title>Catalyst Run Monitor</title>
  <style>
    :root{color-scheme:light;--ink:#17222b;--muted:#66737c;--line:#dce3e6;--paper:#f5f7f6;--card:#fff;--teal:#117c72;--soft:#e6f3f0;--red:#aa3c32;--amber:#9a6b0a}
    *{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
    header{padding:25px max(24px,calc((100vw - 1320px)/2));background:#142a31;color:#f5faf8;display:flex;align-items:center;justify-content:space-between;gap:20px}
    header h1{font-size:22px;margin:0;font-weight:650;letter-spacing:.01em}header p{margin:3px 0 0;color:#bdcfce;font-size:13px}.local{border:1px solid #568078;border-radius:99px;padding:6px 12px;font-size:12px;color:#d9ebe6;white-space:nowrap}
    main{max-width:1320px;margin:25px auto;padding:0 24px;display:grid;grid-template-columns:minmax(300px,390px) minmax(0,1fr);gap:20px}
    .card{background:var(--card);border:1px solid var(--line);border-radius:12px;box-shadow:0 2px 8px #1d383808}.card h2{font-size:16px;margin:0 0 15px}.compose{padding:20px}.compose label{display:block;font-size:13px;font-weight:600;margin:14px 0 6px}.compose textarea,.compose input{width:100%;border:1px solid #cbd5d8;border-radius:8px;padding:10px 11px;font:inherit;background:#fff;color:var(--ink)}.compose textarea{min-height:112px;resize:vertical}.hint{font-size:12px;color:var(--muted);margin:5px 0}.button{border:0;border-radius:8px;background:var(--teal);color:white;padding:10px 15px;font-weight:650;cursor:pointer}.button:disabled{opacity:.55;cursor:wait}.privacy{margin-top:13px;border-left:3px solid #8ac2b3;padding:7px 10px;background:#f1f8f6;color:#53655f;font-size:12px}
    .history{margin-top:16px;padding:18px}.history-head{display:flex;justify-content:space-between;align-items:center}.history-head h2{margin:0}.history-list{display:grid;gap:7px;margin-top:12px;max-height:56vh;overflow:auto}.run-row{width:100%;text-align:left;border:1px solid var(--line);background:#fff;border-radius:8px;padding:10px 11px;color:var(--ink);cursor:pointer}.run-row:hover{border-color:#87b7ac;background:#fbfefd}.run-row strong{display:block;font-size:12px;word-break:break-all}.run-meta{display:flex;justify-content:space-between;gap:8px;color:var(--muted);font-size:12px;margin-top:4px}.pill{display:inline-block;border-radius:99px;padding:2px 8px;background:#eef1f2;color:#48555d;font-size:11px}.pill.success{background:#e3f4ea;color:#267249}.pill.failure,.pill.unresolved,.pill.incomplete,.pill.interrupted{background:#fbe9e6;color:var(--red)}.pill.running{background:#fff3d8;color:var(--amber)}
    .detail{min-width:0}.run-head{padding:19px 21px;display:flex;justify-content:space-between;align-items:flex-start;gap:18px;border-bottom:1px solid var(--line)}.run-head h2{margin:0 0 4px}.run-id{font:12px ui-monospace,SFMono-Regular,Consolas,monospace;color:var(--muted);overflow-wrap:anywhere}.run-status{flex:none}.empty{padding:55px 24px;text-align:center;color:var(--muted)}.empty strong{display:block;color:#34434a;font-size:16px;margin-bottom:5px}.timeline{padding:10px 20px 20px}.event{display:grid;grid-template-columns:150px minmax(0,1fr);gap:15px;padding:13px 0;border-bottom:1px solid #edf0f1}.event:last-child{border-bottom:0}.event-time{font:11px ui-monospace,SFMono-Regular,Consolas,monospace;color:#7b878d;padding-top:2px}.event-title{font-size:13px;font-weight:680}.event-body{font-size:12px;color:#5c6970;margin-top:3px;overflow-wrap:anywhere}.id-token{display:inline-block;margin:4px 5px 0 0;padding:2px 6px;border-radius:5px;background:#f0f4f4;color:#47565c;font:10px ui-monospace,SFMono-Regular,Consolas,monospace}.result{margin:0 20px 18px;padding:13px 14px;border-radius:8px;background:var(--soft);white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}.hidden{display:none!important}
    @media(max-width:850px){main{grid-template-columns:1fr;padding:0 14px;margin:14px auto}.history-list{max-height:260px}header{padding:18px 15px}.event{grid-template-columns:1fr;gap:3px}}
  </style>
</head>
<body>
  <header><div><h1>Catalyst Run Monitor</h1><p>实时查看执行过程，按 Run ID 回放本地记录</p></div><span class="local">仅本机 · 127.0.0.1</span></header>
  <main>
    <section>
      <form id="ask-form" class="card compose">
        <h2>发起任务</h2>
        <label for="message">自然语言任务</label>
        <textarea id="message" required maxlength="20000" placeholder="例如：读取我选中的文件标题，并告诉我来源行号"></textarea>
        <label for="selected-file">本机文件路径（可选）</label>
        <input id="selected-file" maxlength="4096" placeholder="例如：E:\项目\notes.md">
        <p class="hint">仅当任务需要读取本地文件时填写完整路径。</p>
        <button class="button" id="submit" type="submit">开始并观察</button>
        <div id="form-error" class="hint" role="status"></div>
        <div class="privacy">运行记录默认隐藏提示词、标题、文件路径和工具内容，只保存摘要与 SHA-256。完成结果仅在此本机进程内暂存，服务关闭后不保留。</div>
      </form>
      <section class="card history"><div class="history-head"><h2>最近运行</h2><button class="button" id="refresh" type="button">刷新</button></div><div id="runs" class="history-list"></div></section>
    </section>
    <section class="card detail">
      <div id="empty" class="empty"><strong>选择一条运行记录</strong>新任务的事件会在发生时出现在这里。</div>
      <div id="run-view" class="hidden">
        <div class="run-head"><div><h2>运行时间线</h2><div id="run-id" class="run-id"></div></div><span id="run-status" class="pill run-status">—</span></div>
        <div id="result" class="result hidden"></div>
        <div id="timeline" class="timeline"></div>
      </div>
    </section>
  </main>
  <script>
    const labels={"request.started":"运行开始","session.bound":"Runtime 会话已绑定","span.started":"操作开始","span.ended":"操作结束","agent.decision":"Harness 决策","llm.request.started":"模型请求开始","llm.response.received":"模型响应已收到","llm.request.failed":"模型请求失败","binding.resolved":"精确绑定已解析","binding.resolution_failed":"绑定解析失败","tool.call.requested":"模型请求调用工具","authorization.decided":"授权判断","tool.execution.started":"工具执行开始","tool.result":"工具结果","tool.execution.denied":"工具执行被拒绝","tool.execution.unresolved":"工具执行结果未知","source.read.started":"来源读取开始","source.read.completed":"来源读取完成","source.read.failed":"来源读取失败","assistant.final_answer":"最终回答已提交","result.emitted":"任务结果已产生","request.failed":"运行失败","request.interrupted":"运行中断","request.terminal":"运行终态","capabilities.discovered":"能力目录已读取","capabilities.discovery.failed":"能力目录读取失败","component.lifecycle.changed":"组件生命周期变更","component.lifecycle.failed":"组件生命周期失败","component.binding.failed":"组件绑定失败","component.cleanup.failed":"组件清理失败"};
    Object.assign(labels,{"semantic.transition.started":"语义变更开始","semantic.transition.failed":"语义变更失败","semantic.transition.recovered":"语义变更恢复","semantic.source.staged":"语义来源已暂存","semantic.candidate.proposed":"语义候选已提出","semantic.candidate.evidence":"候选证据锚点","semantic.candidate.evaluated":"候选结构评价","semantic.candidate.decided":"管理者决定已记录","semantic.version.accepted":"语义版本已接纳","semantic.version.activated":"语义版本已激活","semantic.version.rolled_back":"语义版本已回退","semantic.version.diffed":"语义版本差异","semantic.consumer.queried":"语义消费者查询","semantic.consumer.meaning_consumed":"消费者关联的含义","semantic.state.inspected":"语义状态已查看"});
    const $=id=>document.getElementById(id);let activeSource=null;let lastSequence=-1;
    function esc(value){return String(value??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}
    function addEvent(event){if(event.sequence<=lastSequence)return;lastSequence=event.sequence;const row=document.createElement("div");row.className="event";const time=document.createElement("div");time.className="event-time";time.textContent=event.timestamp||"";const content=document.createElement("div");const title=document.createElement("div");title.className="event-title";title.textContent=labels[event.event_type]||event.event_type;const detail=document.createElement("div");detail.className="event-body";const fields=[event.status,event.operation&&`操作 ${event.operation}`,event.actor_origin&&`发起方 ${event.actor_origin}`,event.decision,event.candidate_id&&`候选 ${event.candidate_id}`,event.evaluation_id&&`评价 ${event.evaluation_id}`,event.version_id&&`版本 ${event.version_id}`,event.active_version_id&&`活动版本 ${event.active_version_id}`,event.meaning_id&&`含义 ${event.meaning_id}`,event.source_id&&`来源 ${event.source_id}`,event.source_revision&&`修订 ${event.source_revision}`,event.capability_id&&`${event.capability_id}@${event.capability_version||"?"}`,event.component_id&&`组件 ${event.component_id}@${event.component_version||"?"}`,event.transition&&`变更 ${event.transition}`,event.active_version&&`当前版本 ${event.active_version}`,event.in_flight_policy&&`在途规则 ${event.in_flight_policy}`,event.cleanup_status&&`清理 ${event.cleanup_status}`,event.provider_id,event.model,Array.isArray(event.exposed_tools)&&`模型可见工具：${event.exposed_tools.map(item=>item.capability_id?`${item.capability_id}@${item.capability_version||"?"}`:item.tool_name).filter(Boolean).join(", ")||"无"}`,event.error_code,event.input_tokens!=null&&`输入 ${event.input_tokens} tokens`,event.output_tokens!=null&&`输出 ${event.output_tokens} tokens`,event.source_sha256&&`来源 SHA-256 ${event.source_sha256}`,event.line&&`第 ${event.line} 行`].filter(Boolean);detail.textContent=fields.join(" · ");content.append(title,detail);for(const name of ["model_call_id","tool_call_id","execution_id","span_id","transition_id"]){if(event[name]){const token=document.createElement("span");token.className="id-token";token.textContent=`${name}: ${event[name]}`;content.append(token)}}row.append(time,content);$("timeline").append(row);row.scrollIntoView({block:"nearest"})}
    function statusPill(status){const pill=$("run-status");pill.textContent=status||"unknown";pill.className=`pill run-status ${status||"unknown"}`}
    async function refreshRuns(){try{const response=await fetch("/api/runs?limit=100");const runs=await response.json();const host=$("runs");host.replaceChildren();for(const run of runs){const button=document.createElement("button");button.className="run-row";button.type="button";button.onclick=()=>openRun(run.run_id,true);const id=document.createElement("strong");id.textContent=run.run_id;const meta=document.createElement("span");meta.className="run-meta";const kind=document.createElement("span");kind.textContent=run.request_kind||"本地运行";const status=document.createElement("span");status.className=`pill ${run.status}`;status.textContent=run.status;meta.append(kind,status);button.append(id,meta);host.append(button)}}catch(error){$("form-error").textContent="无法读取本地运行记录。"}}
    async function openRun(runId,watch){if(activeSource){activeSource.close();activeSource=null}lastSequence=-1;$("empty").classList.add("hidden");$("run-view").classList.remove("hidden");$("run-id").textContent=runId;$("timeline").replaceChildren();$("result").classList.add("hidden");try{const response=await fetch(`/api/runs/${encodeURIComponent(runId)}`);if(!response.ok)throw Error();const run=await response.json();for(const event of run.events)addEvent(event);statusPill(run.status);if(watch&&run.status==="running"){activeSource=new EventSource(`/api/runs/${encodeURIComponent(runId)}/stream?after=${lastSequence}`);activeSource.addEventListener("run.event",event=>{const item=JSON.parse(event.data);addEvent(item);if(item.event_type==="request.terminal"){statusPill(item.terminal_status);activeSource.close();activeSource=null;showResult(runId);refreshRuns()}});activeSource.addEventListener("run.state",event=>{const state=JSON.parse(event.data);statusPill(state.status);if(state.status!=="running"){activeSource.close();activeSource=null;refreshRuns()}})}else if(run.status!=="running"){showResult(runId)}}catch(error){$("form-error").textContent="无法读取这条运行记录。"}}
    async function showResult(runId){for(let attempt=0;attempt<10;attempt++){try{const response=await fetch(`/api/runs/${encodeURIComponent(runId)}/result`);if(response.ok){const data=await response.json();const output=data.result?.output;const text=output?.answer||output?.title;if(text){$("result").textContent=text;$("result").classList.remove("hidden")}return}if(response.status!==404)return}catch(error){return}await new Promise(resolve=>setTimeout(resolve,100))}}
    $("ask-form").addEventListener("submit",async event=>{event.preventDefault();$("submit").disabled=true;$("form-error").textContent="正在启动…";const payload={message:$("message").value,selected_file:$("selected-file").value||null};try{const response=await fetch("/api/ask",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});const data=await response.json();if(!response.ok)throw Error(data.error?.message||"请求未能启动");$("form-error").textContent=`运行已开始：${data.run_id}`;await openRun(data.run_id,true);refreshRuns()}catch(error){$("form-error").textContent=error.message||"请求未能启动。"}finally{$("submit").disabled=false}});
    $("refresh").onclick=refreshRuns;refreshRuns();setInterval(refreshRuns,5000);
  </script>
</body>
</html>"""


def create_monitor_server(
    workspace: Path | str,
    run_request: Callable[[str, str | None, RunRecorder], dict[str, Any]],
    *,
    port: int = 8765,
    input_root: Path | None = None,
) -> ThreadingHTTPServer:
    """Create a loopback-only monitor. The runner is the existing Gateway path."""
    root = Path(workspace).expanduser().resolve()
    store = JsonlTraceStore(root)
    inputs = Path(input_root).resolve() if input_root is not None else None
    result_root = root / ".catalyst" / "user-results"
    if inputs is not None:
        if not inputs.is_relative_to(root):
            raise ValueError("input root must belong to this workspace")
        inputs.mkdir(parents=True, exist_ok=True)
        if not result_root.resolve().is_relative_to(root):
            raise ValueError("result path escapes workspace")
        result_root.mkdir(parents=True, exist_ok=True)
    csrf = secrets.token_urlsafe(32)

    def result_path(run_id):
        if not re.fullmatch(r"run_[a-f0-9]{32}", run_id):
            return None
        path = result_root / (run_id + ".json")
        return path if path.resolve().is_relative_to(root) else None


    class MonitorHTTPServer(ThreadingHTTPServer):
        daemon_threads = True
        allow_reuse_address = True

        def __init__(self):
            super().__init__(("127.0.0.1", port), MonitorRequestHandler)
            self.workspace = root
            self.trace_store = store
            self.run_request = run_request
            # Shared by additive local Workspace routes; same token and checks,
            # no separate login/session/credential authority.
            self.local_csrf_token = csrf
            self.results: dict[str, dict[str, Any]] = {}
            self.results_lock = threading.RLock()
            self.lease = None
            if inputs is not None:
                self.lease = (result_root / "server.lock").open("a+b")
                self.lease.seek(0, os.SEEK_END)
                if self.lease.tell() == 0:
                    self.lease.write(b"0"); self.lease.flush()
                self.lease.seek(0)
                try:
                    if os.name == "nt":
                        import msvcrt
                        msvcrt.locking(self.lease.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(self.lease.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError:
                    self.lease.close(); self.lease = None
                    super().server_close()
                    raise RuntimeError("This workspace already has an active monitor") from None

        def server_close(self):
            super().server_close()
            if self.lease is not None:
                self.lease.close()
                self.lease = None


    class MonitorRequestHandler(BaseHTTPRequestHandler):
        server: MonitorHTTPServer
        protocol_version = "HTTP/1.1"
        server_version = "CatalystRunMonitor/1.0"

        def log_message(self, _format: str, *_args: Any) -> None:
            # Do not copy local file paths or natural-language input into server logs.
            return

        def _host_allowed(self) -> bool:
            host = self.headers.get("Host", "").casefold()
            port_value = self.server.server_address[1]
            return host in {f"127.0.0.1:{port_value}", f"localhost:{port_value}"}

        def _origin_allowed(self) -> bool:
            origin = self.headers.get("Origin")
            if origin is None:
                return True
            port_value = self.server.server_address[1]
            return origin.casefold() in {
                f"http://127.0.0.1:{port_value}",
                f"http://localhost:{port_value}",
            }

        def _json(self, value: Any, *, status: int = 200) -> None:
            body = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _error(self, code: str, message: str, *, status: int) -> None:
            self._json({"error": {"code": code, "message": message}}, status=status)

        def do_GET(self) -> None:  # noqa: N802
            if not self._host_allowed() or (inputs is not None and not self._origin_allowed()):
                self._error("host_not_allowed", "This monitor accepts loopback requests only.", status=403)
                return
            route = urlsplit(self.path)
            if route.path == "/api/demo" and inputs is not None:
                from .user_session import DEMO_TEXT
                self._json({"name": "organization-demo.txt", "text": DEMO_TEXT, "mode": "MOCK"})
                return
            if route.path == "/api/config" and inputs is not None:
                self._json({"csrf_token": csrf, "mode": getattr(run_request, "mode", "MOCK"),
                            "session_id": getattr(run_request, "session_id", None), "paid_calls_enabled": False})
                return
            if route.path == "/":
                page = _PAGE
                if inputs is not None:
                    page = re.sub(r'<input id="selected-file"[^>]*>', '<input id="selected-file" type="file" accept=".txt,.md,.pptx">', page)
                    page = page.replace('本机文件路径（可选）', '选择 TXT / MD / PPTX 资料')
                    page = page.replace('仅当任务需要读取本地文件时填写完整路径。', '文件仅上传到本机专用输入目录，限 700 KB；不发送到外部模型。')
                    page = page.replace('完成结果仅在此本机进程内暂存，服务关闭后不保留。', '结果和导入资料保存在本机工作目录，重启后可恢复；MOCK 演示不代表真实模型理解。')
                    page = page.replace('const payload={message:$("message").value,selected_file:$("selected-file").value||null};try{', 'try{const config=await (await fetch("/api/config")).json();let selected=null;const file=$("selected-file").files[0];if(file){if(file.size>700000)throw Error("文件超过 700 KB");const bytes=new Uint8Array(await file.arrayBuffer());let binary="";for(const b of bytes)binary+=String.fromCharCode(b);const up=await fetch("/api/uploads",{method:"POST",headers:{"Content-Type":"application/json","X-Catalyst-CSRF":config.csrf_token},body:JSON.stringify({name:file.name,data_base64:btoa(binary)})});const receipt=await up.json();if(!up.ok)throw Error(receipt.error?.message||"导入失败");selected=receipt.selected_file;}const payload={message:$("message").value,selected_file:selected};')
                    page = page.replace('headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)', 'headers:{"Content-Type":"application/json","X-Catalyst-CSRF":config.csrf_token},body:JSON.stringify(payload)')
                    page = page.replace('const text=output?.answer||output?.title;', 'const text=output?.answer||output?.title||data.error?.code||JSON.stringify(data,null,2);')
                    page = page.replace('<h2>发起任务</h2>', '<h2>企业资料 → 本体候选</h2><p class="hint" id="session-info">MOCK 离线演示 · 外部调用关闭</p><button type="button" class="button" id="demo">载入免费演示资料</button>')
                    page = page.replace('<div id="result"', '<div style="padding:12px 20px"><button class="button" id="cancel-run">停止后续步骤</button> <a id="export-run" target="_blank">导出脱敏证据</a></div><div id="result"')
                    page = page.replace('$("run-id").textContent=runId;', '$("run-id").textContent=runId;$("export-run").href=`/api/runs/${encodeURIComponent(runId)}/export`;')
                    page = page.replace('$("result").textContent=text;', 'statusPill(data.state||data.status);$("result").textContent=`${data.mode||""} · ${data.state||data.status}\\n${text}\\n`+JSON.stringify({session_id:data.session_id,source_sha256:data.source_sha256,candidate_id:data.candidate_id,version_id:data.version_id,error:data.error,evaluation:data.evaluation,items:data.proposal?.understanding?.semantic_candidate,unknowns:data.proposal?.understanding?.unknowns,evidence:data.proposal?.understanding?.evidence_refs},null,2);')
                    page = page.replace('labels[event.event_type]||event.event_type', 'event.span_name||labels[event.event_type]||event.event_type')
                    page = page.replace('const fields=[event.status,', 'const fields=[event.status,event.duration_ms!=null&&`${event.duration_ms} ms`,event.attributes&&JSON.stringify(event.attributes),')
                    extra = r"""
    $('demo').onclick=async()=>{const demo=await (await fetch('/api/demo')).json();const file=new File([demo.text],demo.name,{type:'text/plain'});const transfer=new DataTransfer();transfer.items.add(file);$('selected-file').files=transfer.files;$('message').value='请将企业资料整理成组织语义，形成 Ontology 候选并保存待审。';$('form-error').textContent='已选非敏感离线样例。点击开始并观察。';};
    $('cancel-run').onclick=async()=>{const config=await (await fetch('/api/config')).json();const response=await fetch('/api/cancel',{method:'POST',headers:{'Content-Type':'application/json','X-Catalyst-CSRF':config.csrf_token},body:JSON.stringify({run_id:$('run-id').textContent})});const data=await response.json();$('form-error').textContent=data.accepted?'取消已请求；已完成的效果不会撤销，远端计算和费用不作退款保证。':'此运行已结束或不可取消。';};
    fetch('/api/config').then(r=>r.json()).then(c=>{$('session-info').textContent=`${c.mode} · Session ${c.session_id} · 付费调用关闭`;});
"""
                    page = page.replace('</script>',extra+'</script>')
                body = page.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Referrer-Policy", "no-referrer")
                self.end_headers()
                self.wfile.write(body)
                return
            if route.path == "/api/runs":
                try:
                    limit = int(parse_qs(route.query).get("limit", ["100"])[0])
                    runs = self.server.trace_store.list_runs(limit=limit)
                    if inputs is not None:
                        for run in runs:
                            path = result_path(run["run_id"])
                            if path and path.is_file() and run.get("terminal_status") is not None:
                                saved = json.loads(path.read_text(encoding="utf-8"))
                                run["status"] = saved.get("state",run["status"])
                                run["session_id"] = saved.get("session_id")
                    self._json(runs)
                except (ValueError, RuntimeError):
                    self._error("invalid_limit", "The run limit must be between 1 and 1000.", status=400)
                return
            parts = route.path.strip("/").split("/")
            if len(parts) >= 3 and parts[:2] == ["api", "runs"]:
                run_id = unquote(parts[2])
                if not run_id or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for char in run_id):
                    self._error("invalid_run_id", "The Run ID is invalid.", status=400)
                    return
                if len(parts) == 4 and parts[3] == "stream":
                    self._stream(run_id, route.query)
                    return
                inspected = self.server.trace_store.inspect_run(run_id)
                if inspected is None:
                    self._error("run_not_found", "No local run has this Run ID.", status=404)
                    return
                if len(parts) == 4 and parts[3] == "export" and inputs is not None:
                    try:
                        saved = _read_saved_result(result_path(run_id)) or {}
                    except PermissionError:
                        self._error("result_busy", "The saved result is temporarily unavailable.", status=503)
                        return
                    if inspected["terminal_status"] is None:
                        saved = {**saved,"state":"INCOMPLETE","status":"incomplete"}
                    self._json({"run_id":run_id, "session_id":saved.get("session_id"),
                                "state":saved.get("state", inspected["status"]),
                                "candidate_id":saved.get("candidate_id"), "version_id":saved.get("version_id"),
                                "result_sha256":hashlib.sha256(json.dumps(saved,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest() if saved else None,
                                "events":inspected["events"]})
                    return
                if len(parts) == 3:
                    self._json(inspected)
                    return
                if len(parts) == 4 and parts[3] == "result":
                    with self.server.results_lock:
                        result = self.server.results.get(run_id)
                    path = result_path(run_id) if inputs is not None else None
                    if result is None:
                        try:
                            result = _read_saved_result(path)
                        except PermissionError:
                            self._error("result_busy", "The saved result is temporarily unavailable.", status=503)
                            return
                    if result is not None and inputs is not None and inspected["terminal_status"] is None:
                        pending = getattr(run_request, "is_pending", lambda _: False)(run_id)
                        # Result is durably written before the terminal; do not expose
                        # that short commit window as a completed or crashed run.
                        inspected = self.server.trace_store.inspect_run(run_id)
                        if inspected["terminal_status"] is None:
                            if pending:
                                self._error("result_pending", "The run is committing its final evidence.", status=404)
                                return
                            result = {**result,"state":"INCOMPLETE","status":"incomplete"}
                    if result is None:
                        self._error("result_not_available", "This process has no in-memory result for this run.", status=404)
                    else:
                        self._json(result)
                    return
            self._error("route_not_found", "The local route was not found.", status=404)

        def _stream(self, run_id: str, query: str) -> None:
            try:
                after = int(parse_qs(query).get("after", ["-1"])[0])
            except ValueError:
                self._error("invalid_sequence", "The event sequence is invalid.", status=400)
                return
            inspected = self.server.trace_store.inspect_run(run_id)
            if inspected is None:
                self._error("run_not_found", "No local run has this Run ID.", status=404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache, no-store")
            self.send_header("X-Accel-Buffering", "no")
            self.send_header("Connection", "close")
            self.end_headers()
            self.close_connection = True
            last_sequence = after
            try:
                while True:
                    inspected = self.server.trace_store.inspect_run(run_id)
                    if inspected is None:
                        return
                    for item in inspected["events"]:
                        if item["sequence"] <= last_sequence:
                            continue
                        payload = json.dumps(item, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
                        self.wfile.write(
                            f"id: {item['sequence']}\nevent: run.event\ndata: {payload}\n\n".encode("utf-8")
                        )
                        self.wfile.flush()
                        last_sequence = item["sequence"]
                    if inspected["terminal_status"] is not None:
                        return
                    if inspected["status"] == "incomplete":
                        payload = json.dumps({"run_id": run_id, "status": "incomplete"}, separators=(",", ":"))
                        self.wfile.write(f"event: run.state\ndata: {payload}\n\n".encode("utf-8"))
                        self.wfile.flush()
                        return
                    self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
                    time.sleep(0.15)
            except (BrokenPipeError, ConnectionResetError, TimeoutError):
                return

        def do_POST(self) -> None:  # noqa: N802
            if not self._host_allowed() or not self._origin_allowed():
                self._error("origin_not_allowed", "Requests must come from this local monitor.", status=403)
                return
            if inputs is not None and not secrets.compare_digest(self.headers.get("X-Catalyst-CSRF", ""), csrf):
                self._error("csrf_required", "Open the local page before submitting.", status=403)
                return
            route_path = urlsplit(self.path).path
            if route_path not in ({"/api/ask", "/api/uploads", "/api/cancel"} if inputs is not None else {"/api/ask"}):
                self._error("route_not_found", "The local route was not found.", status=404)
                return
            if self.headers.get_content_type() != "application/json":
                self._error("content_type_required", "Send the task as JSON.", status=415)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = 0
            if length <= 0 or length > _MAX_BODY_BYTES:
                # Bounded drain prevents a Windows TCP reset from hiding the 413
                # while the client is still sending a modest oversized upload.
                self.connection.settimeout(2)
                if 0 < length <= 2 * _MAX_BODY_BYTES:
                    try:
                        self.rfile.read(length)
                    except (OSError, TimeoutError):
                        pass
                self.close_connection = True
                self._error("request_size_invalid", "The request is empty or exceeds the local limit.", status=413)
                return
            try:
                body = json.loads(self.rfile.read(length))
            except (json.JSONDecodeError, UnicodeDecodeError):
                self._error("invalid_json", "The task body is not valid JSON.", status=400)
                return
            if not isinstance(body, dict):
                self._error("invalid_request", "The task must be a JSON object.", status=400)
                return
            if route_path == "/api/cancel":
                cancel = getattr(run_request, "cancel", None)
                if set(body) != {"run_id"} or not isinstance(body["run_id"],str):
                    self._error("invalid_request", "A Run ID is required.", status=400)
                    return
                self._json({"accepted":bool(cancel and cancel(body["run_id"]))})
                return
            if route_path == "/api/uploads":
                name = body.get("name")
                try:
                    if not isinstance(name, str) or len(name) > 160 or not re.fullmatch(r"[^/\\:]+\.(txt|md|pptx)", name, re.I):
                        raise ValueError()
                    data = base64.b64decode(body.get("data_base64", ""), validate=True)
                    if not data or len(data) > 700_000:
                        raise ValueError()
                    suffix = Path(name).suffix.lower()
                    digest = hashlib.sha256(data).hexdigest()
                    path = inputs / (digest + suffix)
                    if not path.resolve().is_relative_to(inputs):
                        raise ValueError()
                    if not path.exists():
                        with path.open("xb") as handle:
                            handle.write(data)
                    self._json({"selected_file": str(path), "sha256": digest, "bytes": len(data)}, status=201)
                except (ValueError, TypeError, binascii.Error):
                    self._error("upload_invalid", "Select a TXT, MD or PPTX file under 700 KB.", status=400)
                return
            chat = getattr(getattr(run_request, "settings", None), "chat", None)
            fields = {"message", "selected_file"} | ({"thread_id"} if chat is not None else set())
            if inputs is not None and set(body) - fields:
                self._error("invalid_request", "Only task text and an imported file are accepted.", status=400)
                return
            message = body.get("message")
            selected_file = body.get("selected_file")
            thread_id = body.get("thread_id")
            if "thread_id" in body and (
                inputs is None or chat is None or selected_file is not None or not chat.exists(thread_id)
            ):
                self._error("chat_thread_invalid", "Select an existing conversation for a text message.", status=400)
                return
            if not isinstance(message, str) or not message.strip() or len(message) > _MAX_MESSAGE_CHARS:
                self._error("message_invalid", "Enter a task of 1 to 20000 characters.", status=400)
                return
            if selected_file is not None and (
                not isinstance(selected_file, str) or not selected_file.strip() or len(selected_file) > _MAX_PATH_CHARS
            ):
                self._error("selected_file_invalid", "The local file path is invalid.", status=400)
                return

            if inputs is not None and selected_file is not None:
                candidate = Path(selected_file).resolve()
                if (candidate.parent != inputs or not re.fullmatch(r"[a-f0-9]{64}\.(txt|md|pptx)", candidate.name)
                        or not candidate.is_file() or hashlib.sha256(candidate.read_bytes()).hexdigest() != candidate.stem):
                    self._error("source_not_authorized", "Select a file through the upload control.", status=403)
                    return
            run_id = f"run_{uuid.uuid4().hex}"
            request_id = f"req_{uuid.uuid4().hex}"
            invocation_id = f"inv_{uuid.uuid4().hex}"
            trace_id = uuid.uuid4().hex
            input_bytes = json.dumps(
                {"message": message, "selected_file": selected_file, **({"thread_id": thread_id} if thread_id else {})},
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            recorder = RunRecorder(
                self.server.trace_store,
                run_id=run_id,
                request_id=request_id,
                invocation_id=invocation_id,
                trace_id=trace_id,
            )
            try:
                recorder.start(
                    request_kind="natural_language_ask",
                    input_sha256=hashlib.sha256(input_bytes).hexdigest(),
                    actor="local_cli_user",
                    component="CatalystGateway",
                    selected_file=selected_file,
                    entry_point="local_run_monitor",
                )
            except Exception:
                self._error("trace_write_failed", "The run could not start because local evidence could not be written.", status=503)
                return

            prepare = getattr(run_request, "prepare", None)
            if prepare:
                prepare(recorder)

            def execute() -> None:
                try:
                    if thread_id is None:
                        result = self.server.run_request(message, selected_file, recorder)
                    else:
                        result = self.server.run_request(message, selected_file, recorder, thread_id=thread_id)
                except BaseException as exc:
                    if not recorder.is_finished:
                        try:
                            recorder.event(
                                "request.failed",
                                error_type=type(exc).__name__,
                                error_message=str(exc),
                            )
                            recorder.finish("failure", error_type=type(exc).__name__)
                        except Exception:
                            # The missing terminal remains visible as an incomplete run.
                            pass
                    result = {
                        "run_id": run_id,
                        "status": "failure",
                        "error": {"code": "local_run_failed", "type": type(exc).__name__},
                    }
                if inputs is not None:
                    path = result_path(run_id)
                    temp = path.with_suffix(".tmp")
                    try:
                        with temp.open("w", encoding="utf-8") as handle:
                            json.dump(result, handle, ensure_ascii=False, allow_nan=False)
                            handle.flush()
                            os.fsync(handle.fileno())
                        os.replace(temp, path)
                    except (OSError, ValueError):
                        return  # Missing result is visible; never invent recovered output.
                with self.server.results_lock:
                    self.server.results[run_id] = result

            threading.Thread(target=execute, name=f"catalyst-run-{run_id[-8:]}", daemon=True).start()
            self._json({"run_id": run_id, "status": "running"}, status=202)

    return MonitorHTTPServer()

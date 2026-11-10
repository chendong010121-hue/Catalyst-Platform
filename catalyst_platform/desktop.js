"use strict";

const get = id => document.getElementById(id);
const form = get("chat");
const send = form.querySelector("button");
const selector = get("conversations");
const newButton = get("new-conversation");
const wiki = get("wiki");
const allowNote = get("allow-note");
let status;
let conversationId;
let busy = false;
let pending;

async function api(path, body) {
  const response = await fetch(path, body === undefined ? undefined : {
    method: "POST",
    headers: {"Content-Type": "application/json", "X-Catalyst-CSRF": status.csrf_token},
    body: JSON.stringify(body),
  });
  const value = await response.json();
  if (!response.ok) throw Error(value.error);
  return value;
}

function updateControls() {
  send.disabled = busy || !status?.can_chat;
  selector.disabled = busy || !selector.options.length;
  newButton.disabled = busy || !status;
  wiki.disabled = busy || !status?.available_tools.includes("wiki_search");
  allowNote.disabled = busy || !status?.connection;
  get("use-saved").disabled = busy || !status?.connection?.has_saved_key;
  get("forget-key").disabled = busy || !status?.connection?.has_saved_key;
  get("disconnect").disabled = busy || !status?.can_chat;
  get("connect").querySelector("button").disabled = busy;
}

function renderTurn(turn) {
  const article = document.createElement("article");
  const question = document.createElement("p");
  const answer = document.createElement("p");
  question.className = answer.className = "turn-message";
  question.textContent = "你：" + turn.message;
  answer.textContent = turn.answer === null
    ? "本轮未完成（" + turn.state + "）：" + turn.error
    : "Catalyst：" + turn.answer;
  article.append(question, answer);
  if (turn.has_receipt) {
    const details = document.createElement("details");
    const summary = document.createElement("summary");
    const receipt = document.createElement("a");
    const body = document.createElement("pre");
    summary.textContent = "本轮调用与证据";
    receipt.textContent = "打开落盘记录";
    receipt.href = "/api/runs/" + turn.run_id;
    details.append(summary, receipt, body);
    details.addEventListener("toggle", async () => {
      if (!details.open || body.textContent) return;
      try {
        const result = await api(receipt.href);
        body.textContent = JSON.stringify(result, null, 2);
        for (const call of result.tool_calls) {
          const id = call.result?.data?.artifact_id;
          if (call.name !== "write_workspace_note" || !/^[0-9a-f]{32}$/.test(id)) continue;
          const note = document.createElement("a");
          note.href = "/api/artifacts/" + id;
          note.textContent = "打开本轮保存的笔记";
          details.insertBefore(note, body);
        }
      }
      catch (error) { body.textContent = error.message; }
    });
    article.append(details);
  }
  return article;
}

async function openConversation(id) {
  const {items} = await api("/api/conversations");
  const selected = items.some(item => item.id === id) ? id : items[0]?.id;
  const turns = selected ? (await api("/api/conversations/" + selected)).turns : [];
  selector.replaceChildren(...items.map(item => new Option(item.title, item.id)));
  if (selected) selector.value = selected;
  conversationId = selected;
  history.replaceState(null, "", selected ? "#" + selected : location.pathname);
  get("history").replaceChildren(...turns.map(renderTurn));
}

function showStatus() {
  const model = status.connection;
  const provider = status.provider_mode === "OFFLINE_DEMO" ? "离线演示" :
    status.provider_mode === "SCRIPTED_TRANSPORT" ? "离线模型传输测试" :
    model ? "DeepSeek " + model.model + (model.model_verified ? " · 已收到模型响应" : " · 已配置，等待首轮响应")
    : status.provider_mode;
  get("status").textContent = [
      status.can_chat ? provider : "请配置 DeepSeek 模型",
      status.available_tools.includes("wiki_search") ? "Wiki 已装配" : "Wiki 未装配",
      status.context_strategy ? "上下文已启用" : "上下文已停用",
    ].join(" · ");
  get("build").textContent = "构建 " + (status.build.commit?.slice(0, 12) || "无 Git 身份")
      + " · 桌面摘要 " + status.build.desktop_digest.slice(0, 12);
  get("connection").hidden = !model;
  get("note-label").hidden = !model;
  if (model) {
    get("remember").disabled = !model.can_remember;
    get("connection-limits").textContent = "发送会调用 DeepSeek 并按供应商计费。每轮最多 "
      + model.max_requests + " 次请求，每次最多 " + model.max_output_tokens + " 输出 tokens。";
    get("tools").textContent = "已装配工具：" + [...status.local_tools, ...status.available_tools].join("、");
  }
  updateControls();
}

async function initialize() {
  try {
    status = await api("/api/status");
    if (status.connection && !status.can_chat) get("connection").open = true;
    await openConversation(location.hash.slice(1));
    showStatus();
  } catch (error) {
    get("status").textContent = "无法打开工作台：" + error.message;
  }
}

get("connect").addEventListener("submit", event => {
  event.preventDefault();
  const input = get("api-key");
  const apiKey = input.value;
  input.value = "";
  interact(async () => {
    status = await api("/api/connection", {action: "connect", api_key: apiKey, remember: get("remember").checked});
    showStatus();
  });
});

for (const [id, action] of [["use-saved", "use_saved"], ["disconnect", "disconnect"], ["forget-key", "forget"]]) {
  get(id).addEventListener("click", () => interact(async () => {
    status = await api("/api/connection", {action});
    showStatus();
  }));
}

async function interact(action) {
  if (busy) return;
  busy = true;
  updateControls();
  get("feedback").textContent = "";
  try { await action(); }
  catch (error) { get("feedback").textContent = "操作未完成：" + error.message; }
  finally { busy = false; updateControls(); }
}

newButton.addEventListener("click", () => interact(async () => {
  const {id} = await api("/api/conversations", {});
  await openConversation(id);
  wiki.checked = false;
  allowNote.checked = false;
  get("message").value = "";
}));

selector.addEventListener("change", () => interact(async () => {
  await openConversation(selector.value);
  wiki.checked = false;
  allowNote.checked = false;
  get("message").value = "";
}));

form.addEventListener("submit", event => {
  event.preventDefault();
  const message = get("message").value.trim();
  if (!message || send.disabled) return;
  const allowWiki = wiki.checked;
  const saveNote = allowNote.checked;
  interact(async () => {
    if (!conversationId) {
      conversationId = (await api("/api/conversations", {})).id;
      history.replaceState(null, "", "#" + conversationId);
    }
    if (pending?.conversation_id !== conversationId || pending.message !== message
        || pending.allow_wiki !== allowWiki || pending.allow_note !== saveNote) {
      pending = {
        conversation_id: conversationId, request_id: crypto.randomUUID().replaceAll("-", ""),
        message, allow_wiki: allowWiki, allow_note: saveNote,
      };
    }
    get("feedback").textContent = "正在处理…";
    try {
      await api("/api/chat", pending);
      get("message").value = "";
      wiki.checked = false;
      allowNote.checked = false;
      pending = null;
    } finally {
      await openConversation(conversationId);
      status = await api("/api/status");
      showStatus();
    }
    get("feedback").textContent = "";
  });
});

initialize();

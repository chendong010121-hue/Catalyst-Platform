"use strict";

const get = id => document.getElementById(id);
const form = get("chat");
const send = form.querySelector("button");
let status;

async function initialize() {
  try {
    const response = await fetch("/api/status");
    if (!response.ok) throw Error("无法读取工作台状态");
    status = await response.json();
    const provider = status.provider_mode === "OFFLINE_DEMO" ? "离线演示" : status.provider_mode;
    get("status").textContent = [
      status.can_chat ? provider : "未配置模型",
      status.available_tools.includes("wiki_search") ? "Wiki 已装配" : "Wiki 未装配",
    ].join(" · ");
    get("build").textContent = "构建 " + (status.build.commit?.slice(0, 12) || "无 Git 身份")
      + " · 桌面摘要 " + status.build.desktop_digest.slice(0, 12);
    get("wiki").disabled = !status.available_tools.includes("wiki_search");
    send.disabled = !status.can_chat;
  } catch (error) {
    get("status").textContent = error.message;
  }
}

form.addEventListener("submit", async event => {
  event.preventDefault();
  const message = get("message").value.trim();
  if (!message || send.disabled) return;
  const allowWiki = get("wiki").checked;
  get("wiki").checked = false;
  send.disabled = true;
  get("turn").hidden = false;
  get("question").textContent = "你：" + message;
  get("result").textContent = "正在处理…";
  get("evidence").hidden = true;
  get("evidence").open = false;
  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: {"Content-Type": "application/json", "X-Catalyst-CSRF": status.csrf_token},
      body: JSON.stringify({message, allow_wiki: allowWiki}),
    });
    const result = await response.json();
    if (!response.ok) throw Error(result.error);
    get("result").textContent = result.answer ?? ("运行停止：" + result.error);
    get("receipt").href = "/api/runs/" + result.run_id;
    get("details").textContent = JSON.stringify(result, null, 2);
    get("evidence").hidden = false;
  } catch (error) {
    get("result").textContent = "本轮未完成：" + error.message;
  } finally {
    send.disabled = false;
  }
});

initialize();

# Workplace 首页与对话

首页输入并发送时创建新对话。最近工作把同一对话的多个调用合为一项，以第一条消息作为标题；点击后继续原对话。每轮调用仍保留独立的运行、账目与观测记录。原有 Agents、Wiki、Enterprise、Observability、Reviews、Development 页面保留。

输入区右侧显示三个入口：

- 上下文：最近一次已计量请求的实际输入 tokens / 该次运行声明的输入上限。它不是草稿实时估算，也不是供应商理论上下文窗口。历史记录未保存用量时显示“未记录”，不补造数字。
- 访问权限：展示现有授权状态与预留的策略选项。切换尚未接入，选项禁用，不扩大工具或文件权限。
- 模型：显示当前配置的模型，点击打开既有设置页。保存的凭证与活动连接的状态放在提示中。

历史选取仍通过已注册的 `context.chat_history` 服务。默认按预算选择近期完整轮次，历史预算最多 8192 个估算 tokens，必要时减少；没有启用自动摘要压缩。省略旧轮次不会删除其运行记录。本批没有修改上下文策略或模型调用权限。

验证使用本地 HTTP 工作台、脚本化 Provider 和合成凭证，包含进程重启后恢复、对话隔离、从最近工作续聊、实际用量读回、七个页面和手机宽度检查。不会调用真实模型，也不会读取正式凭证。

```powershell
python -m pytest -q tests/test_workspace_model_settings.py tests/test_workspace_settings_http.py tests/test_daily_connection_http.py tests/test_wiki_asset_chat.py tests/test_minimum_product.py tests/test_test_infrastructure_http.py tests/test_capability_release.py tests/test_plugin_composition.py
node tests/browser/daily_development_infrastructure.cjs <全新证据目录> <全新测试工作区>
```

# Workplace 首页与对话

首页输入并发送时创建新对话。最近工作把同一对话的多个调用合为一项，以第一条消息作为标题；点击后继续原对话。每轮调用仍保留独立的运行、账目与观测记录。原有 Agents、Wiki、Enterprise、Observability、Reviews、Development 页面保留。

输入区右侧显示三个入口：

- 上下文：最近一次已计量请求的实际输入 tokens / 该次运行声明的输入上限。它不是草稿实时估算，也不是供应商理论上下文窗口。历史记录未保存用量时显示“未记录”，不补造数字。
- 访问权限：展示现有授权状态与预留的策略选项。切换尚未接入，选项禁用，不扩大工具或文件权限。
- 模型：显示当前配置的模型，点击打开既有设置页。保存的凭证与活动连接的状态放在提示中。

历史选取仍通过已注册的 `context.chat_history` 服务。默认按预算选择近期完整轮次，历史预算最多 8192 个估算 tokens，必要时减少；没有启用自动摘要压缩。省略旧轮次不会删除其运行记录。本批没有修改上下文策略或模型调用权限。

## 消息与可观测性

聊天气泡借鉴 `kubai-message-bubbles 1.0.0` 的 Cirrus 轻薄材质与柔和入场，适配白底、深色正文和原有字号。用户消息靠右、助手靠左；保留输入框、原图标、等待提示及消息加载流程。没有天空背景、外部字体或新增视觉运行依赖。减少动态效果的系统设置会关闭气泡运动；用户向上阅读时保持位置，在底部时跟随新消息。

每轮回复下显示请求时间、已报告输入/输出 Token、平均输出速度、可归属的费用估算、执行耗时，以及复制和调用详情。聊天和 Observability 使用同一份 R4 投影、同一读取队列与缓存。

- 输出速度是输出 Token 除以模型请求完整耗时，含等待，并非纯解码速度。缺用量或耗时则不计算。
- 执行耗时优先读终态字段，缺少时读取 `catalyst.run` 根 Span；不相加嵌套 Span。
- 费用沿用可归属的单轮回执资格，不使用 scope 累计余额冒充单轮费用；没有可归属回执就标未记录，不推算为零。
- Observability 按持久化的 `chat.thread_id` 折叠为对话，展开才显示各轮。其他任务独立保留，原始运行和事件不合并、不删除。
- 汇总只涵盖当前载入记录，并逐项显示用量、耗时和费用的覆盖轮数。筛选命中一轮时，保留同一对话中已载入的其他轮次。详情链接绑定对话及运行 id，刷新后可重开；从侧栏进入默认显示折叠列表。

前端投影回归：`node --test tests/frontend/observability.test.cjs`。浏览器回归另外验证对话展开/收起、详情跳转、独立对话隔离和复制内容一致性，使用脚本化模型，不作为真实模型性能测量。

验证使用本地 HTTP 工作台、脚本化 Provider 和合成凭证，包含进程重启后恢复、对话隔离、从最近工作续聊、实际用量读回、七个页面和手机宽度检查。不会调用真实模型，也不会读取正式凭证。

```powershell
python -m pytest -q tests/test_workspace_model_settings.py tests/test_workspace_settings_http.py tests/test_daily_connection_http.py tests/test_wiki_asset_chat.py tests/test_minimum_product.py tests/test_test_infrastructure_http.py tests/test_capability_release.py tests/test_plugin_composition.py
node tests/browser/daily_development_infrastructure.cjs <全新证据目录> <全新测试工作区>
```

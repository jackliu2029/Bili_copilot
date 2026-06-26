# 项目范围 / Scope

## 当前 PoC 已做什么

- 项目骨架（`pyproject.toml`、`src/`、`tests/`、`docs/`、`outputs/`、`.gitignore`、`README.md`）。
- B站标准 BV 链接、带 `p` 参数的多P链接本地解析（`b23.tv` 短链识别为待解析，当前不自动联网重定向）。
- 视频元数据获取（标题、UP主、aid、cid、pages、时长、简介）。
- 字幕轨列表获取与选择策略：人工简体中文优先，AI 简体中文次之，再其他中文，最后兜底。
- 字幕正文下载与标准化（保留 `start`、`end`、`text`）。
- 原始内容包导出：JSON、TXT、Markdown，共 7 个文件。
- 无 Cookie 模式与 `--cookie-file` 登录态模式。
- Cookie 文件读取、解析、脱敏与安全校验。
- 登录态下播放器接口 `subtitle_url` 缺失的最小重试。
- 状态表达：`success`、`no_subtitle`、`login_required`、`subtitle_url_missing`、`empty_subtitle`。

## 当前 PoC 明确不做

- AI 总结、学习笔记生成、知识库构建。
- ASR / OCR / RAG。
- 浏览器插件、Web UI、GUI、桌面软件、移动端。
- 收藏夹/UP主/搜索批量。
- 评论、弹幕、视频下载。
- 账号系统、扫码登录、自动读取浏览器 Cookie、WebBridge、云服务、商业化功能。
- Git 初始化、依赖安装由用户按需自行管理。

## 当前 PoC 边界

当前 PoC 只做“原始内容提取”，不做“内容二次加工”与“平台化功能”。

后续如果项目扩展到学习笔记、总结、知识库或浏览器插件，必须重新经过 ChatGPT 方案设计、用户确认和阶段任务书批准，不能由 Kimi Code 自行扩展。

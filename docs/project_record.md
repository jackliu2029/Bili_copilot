# 项目记录 / Project Record

## 2026-06-22 执行前双向校准

- 确认 Kimi Code CLI 身份：本地执行工程师 / coding agent。
- 确认 ChatGPT 角色：项目军师 / 项目经理 / 架构师 / 总指挥。
- 确认用户角色：项目主人 / 甲方 / 最终验收人。
- 确认项目定位：B站视频原始内容提取器（Raw Content Extractor），不是 AI 总结器。
- 确认 PoC 核心原则：宁可不总结，也不能丢字幕原文；功能少但要原始内容低损耗、可追溯、可复查。
- 确认 references 目录为只读参考资料库，不复制、不导入、不修改。
- 确认当前环境：Python 3.14.4，pip 26.0.1，非 Git 仓库。
- 确认第一阶段目标：项目安全初始化 + 骨架创建，不实现业务逻辑、不安装依赖、不初始化 Git。

## 2026-06-22 PoC 核心闭环完成

- 全量测试：`188 passed`。
- 核心模块交付：`url_parser.py`、`bilibili_client.py`、`cookie_config.py`、`subtitle_selector.py`、`subtitle_fetcher.py`、`normalizer.py`、`pipeline.py`、`exporter.py`、`cli.py`。
- 登录态真实 PoC 验证成功：
  - `BV1Ae411g7VM`：`success`，811 段字幕，主题与 iPhone 14 Pro 评测一致；
  - `BV1gq4y117Mv`：`success`，344 段字幕，主题与雅思备考一致。
- 输出区已清理，仅保留 `outputs/.gitkeep` 与 `outputs/login_stability_check/`。
- Cookie 文件仍位于用户本机路径，未进入项目目录、未进入输出包、未写入 README/docs。
- references 目录未被触碰。

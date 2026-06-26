# 架构说明 / Architecture

## 模块划分（当前已实现）

```text
src/bili_copilot/
├── __init__.py              # 包版本信息
├── cli.py                   # 命令行入口
├── models.py                # 数据模型（VideoMeta、PageInfo、SubtitleTrack、TranscriptSegment、ExtractionResult）
├── url_parser.py            # B站输入链接本地解析（标准库实现，不联网）
├── bilibili_client.py       # B站公开视频信息获取层（视频元数据、分P、字幕轨列表；不下载字幕正文）
├── cookie_config.py         # 本机 Cookie 文件读取与脱敏工具（不主动读取浏览器、不请求网络）
├── subtitle_selector.py     # 字幕轨选择策略（纯本地逻辑，不联网、不下载字幕正文）
├── subtitle_fetcher.py      # 字幕正文 JSON 下载层（只请求 subtitle_url，不处理视频接口）
├── normalizer.py            # 字幕 JSON 标准化层（from/to/content → TranscriptSegment）
├── pipeline.py              # 主流程编排层（模块串联，不直接实现网络细节或导出细节）
├── exporter.py              # 本地导出层（JSON/TXT/Markdown，不联网）
└── utils.py                 # 通用工具函数
```

## 数据流（当前已实现）

```text
用户输入 URL
    │
    ▼
URL 归一化与验证
    │
    ▼
B站视频元数据获取
    │
    ▼
字幕轨列表获取与选择
    │
    ▼
字幕正文下载
    │
    ▼
导出 JSON / TXT / Markdown
    │
    ▼
outputs/
```

## 设计约束

- 所有路径使用 `pathlib.Path`，禁止硬编码 `C:\`、`/c/code` 或 Git Bash 专用路径。
- 所有模型使用 `dataclasses` 或 `pydantic`，便于序列化与类型检查。
- CLI 使用标准库 `argparse`，保持最小依赖。
- 输出目录与源码目录分离，便于清理与版本控制。

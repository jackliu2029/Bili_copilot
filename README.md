# Bili_copilot

B站视频原始内容提取器 / Raw Content Extractor

## 定位

Bili_copilot 不是 AI 总结器，不是视频分析器，也不是学习笔记生成器。

当前 PoC 已完成：输入一个 B站分享链接，输出该视频的**原始内容包**（元数据、分P信息、字幕轨、字幕原文与时间戳），供用户自行复制或上传给 ChatGPT、Kimi、Claude 等外部 AI 继续分析。

长期上，Bili_copilot 可以服务于个人学习视频处理流程；但当前 PoC 只负责原始内容提取，不负责总结、分析或学习笔记生成。

## 当前阶段

PoC 核心闭环已完成，包含：

- 单个 B站视频链接解析（标准 BV 链接、带 `p` 参数的多P链接）。
- 视频元数据获取（标题、UP主、简介、时长、aid、cid、pages）。
- 分P信息保存。
- 字幕轨列表获取；中文字幕优先，人工中文优先于 AI 中文。
- 主字幕轨正文下载，保留每条字幕的 `start`、`end`、`text`。
- 导出 JSON、TXT、Markdown 原始内容包。
- 无 Cookie 模式与 `--cookie-file` 登录态模式。
- 状态表达：`success`、`no_subtitle`、`login_required`、`subtitle_url_missing`、`empty_subtitle`。
- 全量测试通过。

### PoC 明确不做

- AI 总结、学习笔记生成。
- ASR、OCR、RAG。
- 浏览器插件、Web UI、GUI、桌面软件、移动端。
- 收藏夹批量、UP主批量、搜索结果批量。
- 评论提取、弹幕提取、视频下载。
- 账号系统、扫码登录、Cookie 自动读取、WebBridge、云服务、商业化功能。

## 安装

在项目根目录执行 editable 安装：

```bash
python -m pip install -e .
```

或直接从源码运行：

```bash
python -m bili_copilot.cli "B站链接" --output outputs
```

## 使用

### 默认无 Cookie

```bash
python -m bili_copilot.cli "https://www.bilibili.com/video/BVxxxx/" --output outputs
```

### 使用本机 Cookie 文件启用登录态字幕

```bash
python -m bili_copilot.cli "https://www.bilibili.com/video/BVxxxx/" \
  --output outputs \
  --cookie-file "C:\path\to\cookie_file.txt"
```

Cookie 文件格式为 `key=value` 多行，由用户自行在本机准备，应放在项目目录之外；不要把 Cookie 内容粘贴到命令行、聊天、README、输出文件或仓库。

### 环境变量方式

也可设置 `BILI_COOKIE_FILE` 指向 Cookie 文件路径：

```bash
export BILI_COOKIE_FILE="C:\path\to\cookie_file.txt"
python -m bili_copilot.cli "https://www.bilibili.com/video/BVxxxx/" --output outputs
```

## 输出内容包

每个视频会在 `--output` 目录下创建以 `BV号_视频标题` 命名的子目录，包含 7 个文件：

```text
00_video_meta.json            # 视频元数据
01_pages.json                 # 分P信息
02_subtitle_tracks.json       # 可用字幕轨列表
03_transcript_raw.json        # 完整结果（含状态、segments、message）
04_transcript_with_timestamps.txt  # 带时间戳的字幕原文
05_transcript_plain.txt       # 纯文字幕原文
06_content_for_ai.md          # 合并后的内容包，可直接复制给外部 AI
```

## 安全边界

- 不读取、不索要、不存储 Cookie、`SESSDATA`、`bili_jct`、`DedeUserID`、access token。
- 不把敏感凭证写入代码、日志、README、输出文件或仓库。
- 不主动读取浏览器 Cookie。
- 不在未经用户确认的情况下删除、覆盖文件或安装依赖。

## 登录态字幕说明

当前默认不使用 Cookie。登录态字幕可通过 `--cookie-file` 指向本机 Cookie 文件启用，或设置 `BILI_COOKIE_FILE` 环境变量指向 Cookie 文件路径。不要把 Cookie 粘贴到聊天、日志、README 或输出文件中。

## 本地参考资料

`references/` 目录（如果存在）仅用于本机参考，不属于项目源码，不应提交到仓库。

## 许可证

暂未决定。未来如需公开发布，再统一确定许可证。


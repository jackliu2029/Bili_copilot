"""CLI entry point for Bili_copilot."""

import argparse
import os
import sys
from pathlib import Path

from bili_copilot.cookie_config import (
    CookieConfigError,
    get_cookie_file_from_env,
    load_cookie_header_from_file,
)
from bili_copilot.pipeline import PipelineError, run_pipeline


def _resolve_cookie_header(cookie_file: str | None) -> str | None:
    """Resolve the Cookie header from --cookie-file or BILI_COOKIE_FILE env.

    Returns ``None`` if neither is provided. Cookie contents are never printed
    or returned in exception messages.
    """
    path_source = cookie_file
    if not path_source:
        env_path = get_cookie_file_from_env(os.environ)
        if env_path is not None:
            path_source = str(env_path)

    if not path_source:
        return None

    return load_cookie_header_from_file(path_source)


def main(argv: list[str] | None = None) -> int:
    """Entry point for the bili-copilot CLI."""
    parser = argparse.ArgumentParser(
        prog="bili-copilot",
        description="B站视频原始内容提取器 / Raw Content Extractor",
    )
    parser.add_argument(
        "url",
        help="B站分享链接或 BV 号",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="outputs",
        help="输出目录（默认：outputs）",
    )
    parser.add_argument(
        "--cookie-file",
        default=None,
        help="本机 Cookie 文件路径（key=value 多行格式）。不粘贴 Cookie 内容。",
    )

    args = parser.parse_args(argv)

    try:
        cookie_header = _resolve_cookie_header(args.cookie_file)
        output_dir = run_pipeline(
            input_url=args.url,
            output_base=Path(args.output),
            cookie_header=cookie_header,
        )
    except PipelineError as exc:
        print(f"[错误] {exc}", file=sys.stderr)
        return 1
    except CookieConfigError as exc:
        print(f"[Cookie 文件错误] {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 - last-resort user-facing message
        print(f"[未预期错误] {exc}", file=sys.stderr)
        return 1

    print(f"内容包已导出：{output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

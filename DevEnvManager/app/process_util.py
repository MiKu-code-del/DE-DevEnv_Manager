# -*- coding: utf-8 -*-
"""子进程执行工具：隐藏控制台窗口、稳健解码输出。

背景：部分 Python 发行版默认开启 UTF-8 模式（PYTHONUTF8=1），而 Windows
控制台命令常使用系统 ANSI 代码页（中文系统为 GBK），直接 ``text=True``
会触发 UnicodeDecodeError。这里统一捕获字节，再按 utf-8 -> mbcs 的顺序解码。
"""
from __future__ import annotations

import subprocess

CREATE_NO_WINDOW = 0x08000000


def decode_bytes(data: bytes | None) -> str:
    if not data:
        return ""
    for enc in ("utf-8", "mbcs"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def run_cmd(args, shell: bool = False, timeout: int = 30) -> tuple[str, str, int]:
    """执行命令，返回 (stdout 文本, stderr 文本, 退出码)。"""
    proc = subprocess.run(
        args,
        shell=shell,
        capture_output=True,
        timeout=timeout,
        creationflags=CREATE_NO_WINDOW,
    )
    return (decode_bytes(proc.stdout),
            decode_bytes(proc.stderr),
            proc.returncode)
